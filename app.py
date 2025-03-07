# Import necessary libraries
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
import base64
import io
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global key store for direct encryption/decryption
key_store = {}

# Generate encryption key
def generate_key():
    return Fernet.generate_key()

def encrypt_file(file_data, key=None, use_key=True):
    if key is None:
        key = generate_key()
    
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(file_data)
    
    if not use_key:
        combined_data = key + b"||KEY_SEPARATOR||" + encrypted_data
        return combined_data, key
    return encrypted_data, key


# Decrypt file
def decrypt_file(encrypted_data, key=None):
    if key is None or b"||KEY_SEPARATOR||" in encrypted_data:
        parts = encrypted_data.split(b"||KEY_SEPARATOR||", 1)
        if len(parts) == 2:
            key = parts[0]
            encrypted_data = parts[1]
    
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data)
    return decrypted_data

# Encrypt text
def encrypt_text_data(text, key=None, use_key=True):
    if key is None:
        key = generate_key()
        
    fernet = Fernet(key)
    encoded_text = text.encode('utf-8')
    encrypted_text = fernet.encrypt(encoded_text)
    
    # For direct method, combine key and encrypted text
    if not use_key:
        # Store key and encrypted data together with a separator
        return key + b"||KEY_SEPARATOR||" + encrypted_text, key
    return encrypted_text, key

# Decrypt text
def decrypt_text(encrypted_text, key=None):
    # Check if this is direct-encrypted text (contains embedded key)
    if key is None or b"||KEY_SEPARATOR||" in encrypted_text:
        # Extract the key and actual encrypted text
        parts = encrypted_text.split(b"||KEY_SEPARATOR||", 1)
        if len(parts) == 2:
            key = parts[0]
            encrypted_text = parts[1]
    
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_text)
    return decrypted_data.decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_key', methods=['POST'])
def generate_key_route():
    key = generate_key()
    return jsonify({'success': True, 'key': key.decode('utf-8')})

@app.route('/encrypt_file', methods=['POST'])
def encrypt_file_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'file' not in request.files or request.files['file'].filename == '':
        return redirect(url_for('index'))
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_data = file.read()
    
    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
        else:
            key = generate_key()
            
        encrypted_data, used_key = encrypt_file(file_data, key, use_key=use_key)
        
        # Create a unique file ID
        file_id = str(uuid.uuid4())
        
        # Store the encrypted data temporarily
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file_id)
        
        with open(temp_file_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Store the key and filename in session
        session['encryption_key'] = used_key.decode('utf-8')
        session['encrypted_filename'] = filename
        session['file_id'] = file_id
        
        # Redirect to result page first
        return redirect(url_for('file_encryption_result'))
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/file_encryption_result')
def file_encryption_result():
    key = session.get('encryption_key', '')
    filename = session.get('encrypted_filename', '')
    file_id = session.get('file_id', '')
    
    if not key or not filename or not file_id:
        return redirect(url_for('index'))
    
    # Keep the file_id in session, but clear other sensitive data
    session.pop('encryption_key', None)
    session.pop('encrypted_filename', None)
    
    return render_template('result.html', key=key, filename=filename, file_id=file_id)

@app.route('/download_encrypted_file/<file_id>')
def download_encrypted_file(file_id):
    # Security check - validate file_id format
    try:
        uuid_obj = uuid.UUID(file_id)
    except ValueError:
        return render_template('error.html', error="Invalid file ID")
    
    # Get filename from session
    filename = session.get('encrypted_filename', '')
    
    # Clear filename from session
    session.pop('encrypted_filename', None)
    session.pop('file_id', None)
    
    # Check if the temp file exists
    temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp', file_id)
    
    if not os.path.exists(temp_file_path):
        return render_template('error.html', error="File not found or expired")
    
    try:
        # Read the file
        with open(temp_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Create a BytesIO object
        memory_file = io.BytesIO(encrypted_data)
        memory_file.seek(0)
        
        # Delete the temp file
        os.remove(temp_file_path)
        
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f"encrypted_{filename}",
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        return render_template('error.html', error=str(e))
    
@app.route('/decrypt_file', methods=['POST'])
def decrypt_file_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'file' not in request.files or request.files['file'].filename == '':
        return redirect(url_for('index'))
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_data = file.read()
    
    if filename.startswith('encrypted_'):
        original_filename = filename[10:]
    else:
        original_filename = filename

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            decrypted_data = decrypt_file(file_data, key)
        else:
            # Use embedded key for direct decryption
            decrypted_data = decrypt_file(file_data)

        memory_file = io.BytesIO(decrypted_data)
        memory_file.seek(0)

        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f"decrypted_{original_filename}",
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/encrypt_text', methods=['POST'])
def encrypt_text_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'text' not in request.form or not request.form['text'].strip():
        return redirect(url_for('index'))
    
    text = request.form['text'].strip()
    
    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
        else:
            key = generate_key()

        encrypted_text, used_key = encrypt_text_data(text, key, use_key=use_key)
        encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')

        return render_template('result.html', encrypted_text=encrypted_b64, key=used_key.decode('utf-8'))
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/decrypt_text', methods=['POST'])
def decrypt_text_route():
    use_key = request.form.get('use_key') == 'true'

    if 'text' not in request.form or not request.form['text'].strip():
        return render_template('error.html', error="Encrypted text is required.")

    encrypted_b64 = request.form['text'].strip()

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            encrypted_text = base64.b64decode(encrypted_b64)
        else:
            return render_template('error.html', error="Decryption key is required.")

        decrypted_text = decrypt_text(encrypted_text, key)

        return render_template('decrypt_result.html', decrypted_text=decrypted_text)

    except Exception as e:
        return render_template('error.html', error=f"Decryption failed: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Change 5001 to your desired port