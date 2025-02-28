# Import necessary libraries
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
import base64
import io

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

# Save key to file or return it
def save_or_return_key(key, save=False):
    if save:
        with open('encryption_key.key', 'wb') as key_file:
            key_file.write(key)
    return key

# Encrypt file
def encrypt_file(file_data, key=None):
    if key is None:
        key = generate_key()
    
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(file_data)
    return encrypted_data, key

# Decrypt file
def decrypt_file(encrypted_data, key):
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data)
    return decrypted_data

# Encrypt text
def encrypt_text(text, key=None):
    if key is None:
        key = generate_key()
        
    fernet = Fernet(key)
    encoded_text = text.encode('utf-8')
    encrypted_text = fernet.encrypt(encoded_text)
    return encrypted_text, key

# Decrypt text
def decrypt_text(encrypted_text, key):
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
    
    # Use provided key or generate a new one
    if use_key and 'key' in request.form and request.form['key'].strip():
        try:
            key = request.form['key'].strip().encode('utf-8')
            encrypted_data, _ = encrypt_file(file_data, key)
        except Exception as e:
            return render_template('error.html', error=str(e))
    else:
        encrypted_data, key = encrypt_file(file_data)
        
        # Store key for direct decryption (without key)
        file_id = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')
        key_store[file_id] = key
        
        # Add identifier to filename
        if not use_key:
            filename = f"{file_id}_{filename}"
    
    # Create response with encrypted file
    memory_file = io.BytesIO(encrypted_data)
    memory_file.seek(0)
    
    # Return the key and encrypted file
    if use_key:
        return render_template('result.html', 
                              file_encrypted=True,
                              encrypted_filename=f"encrypted_{filename}",
                              key=key.decode('utf-8'))
    else:
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f"encrypted_{filename}",
            mimetype='application/octet-stream'
        )

@app.route('/decrypt_file', methods=['POST'])
def decrypt_file_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'file' not in request.files or request.files['file'].filename == '':
        return redirect(url_for('index'))
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_data = file.read()
    
    # Remove 'encrypted_' prefix if it exists
    if filename.startswith('encrypted_'):
        original_filename = filename[10:]
    else:
        original_filename = filename
    
    try:
        if use_key:
            # Use provided key
            if 'key' not in request.form or not request.form['key'].strip():
                return render_template('error.html', error="Decryption key is required")
            
            key = request.form['key'].strip().encode('utf-8')
        else:
            # Extract file_id from filename for direct decryption
            if '_' not in original_filename:
                return render_template('error.html', error="Invalid file format for direct decryption")
            
            file_id, original_filename = original_filename.split('_', 1)
            
            if file_id not in key_store:
                return render_template('error.html', error="Cannot find decryption key for this file")
            
            key = key_store[file_id]
        
        decrypted_data = decrypt_file(file_data, key)
        
        # Create response with decrypted file
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
    
    # Use provided key or generate a new one
    if use_key and 'key' in request.form and request.form['key'].strip():
        try:
            key = request.form['key'].strip().encode('utf-8')
            encrypted_text, _ = encrypt_text(text, key)
        except Exception as e:
            return render_template('error.html', error=str(e))
    else:
        encrypted_text, key = encrypt_text(text)
        
        # For direct decryption, store text ID with the encrypted text
        if not use_key:
            text_id = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')
            key_store[text_id] = key
            
            # Prepend text_id to encrypted text (base64 encoded)
            encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
            encrypted_b64 = f"{text_id}:{encrypted_b64}"
            
            return render_template('result.html', 
                                  encrypted_text=encrypted_b64)
    
    # Convert to base64 for display
    encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
    
    # Return the key and encrypted text
    return render_template('result.html', 
                          encrypted_text=encrypted_b64, 
                          key=key.decode('utf-8'))

@app.route('/decrypt_text', methods=['POST'])
def decrypt_text_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'text' not in request.form or not request.form['text'].strip():
        return redirect(url_for('index'))
    
    encrypted_b64 = request.form['text'].strip()
    
    try:
        if use_key:
            # Use provided key
            if 'key' not in request.form or not request.form['key'].strip():
                return render_template('error.html', error="Decryption key is required")
            
            key = request.form['key'].strip().encode('utf-8')
            encrypted_text = base64.b64decode(encrypted_b64)
        else:
            # Extract text_id from encoded text
            if ':' not in encrypted_b64:
                return render_template('error.html', error="Invalid text format for direct decryption")
            
            text_id, encrypted_b64 = encrypted_b64.split(':', 1)
            
            if text_id not in key_store:
                return render_template('error.html', error="Cannot find decryption key for this text")
            
            key = key_store[text_id]
            encrypted_text = base64.b64decode(encrypted_b64)
        
        decrypted_text = decrypt_text(encrypted_text, key)
        
        return render_template('result.html', 
                              decrypted_text=decrypted_text)
    
    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)