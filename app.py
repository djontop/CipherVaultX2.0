from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
import base64
import io
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

key_store = {}

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

def encrypt_text(text, key=None, use_key=True):
    if key is None:
        key = generate_key()
        
    fernet = Fernet(key)
    encoded_text = text.encode('utf-8')
    encrypted_text = fernet.encrypt(encoded_text)

    if not use_key:
        return key + b"||KEY_SEPARATOR||" + encrypted_text, key
    return encrypted_text, key

# Decrypt text
def decrypt_text(encrypted_text, key=None):

    if key is None or b"||KEY_SEPARATOR||" in encrypted_text:

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
    start_time = time.time()  # Start timing

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
            encrypted_data, _ = encrypt_file(file_data, key, use_key=True)
        else:
            encrypted_data, key = encrypt_file(file_data, use_key=False)

        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Encryption Time: {time_taken:.2f} ms")  # Print to console

        
        memory_file = io.BytesIO(encrypted_data)
        memory_file.seek(0)
    
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f"encrypted_{filename}",
            mimetype='application/octet-stream'
        ), {'key': key.decode('utf-8')}

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
    
    start_time = time.time()  # Start timing

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            decrypted_data = decrypt_file(file_data, key)
        else:
            decrypted_data = decrypt_file(file_data)

        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Decryption Time: {time_taken:.2f} ms")  # Print to console

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
    start_time = time.time()  # Start timing

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
        else:
            key = generate_key()

        encrypted_text, _ = encrypt_text(text, key)
        encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Text Encryption Time: {time_taken:.2f} ms")  # Print to console

        return render_template('result.html', encrypted_text=encrypted_b64, key=key.decode('utf-8'))
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/decrypt_text', methods=['POST'])
def decrypt_text_route():
    use_key = request.form.get('use_key') == 'true'

    if 'text' not in request.form or not request.form['text'].strip():
        return render_template('error.html', error="Encrypted text is required.")

    encrypted_b64 = request.form['text'].strip()
    start_time = time.time()  # Start timing

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            encrypted_text = base64.b64decode(encrypted_b64)
        else:
            return render_template('error.html', error="Decryption key is required.")

        decrypted_text = decrypt_text(encrypted_text, key)
        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Text Decryption Time: {time_taken:.2f} ms")  # Print to console

        return render_template('decrypt_result.html', decrypted_text=decrypted_text)

    except Exception as e:
        return render_template('error.html', error=f"Decryption failed: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
