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
def encrypt_file(file_data, key):
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(file_data)
    return encrypted_data

# Encrypt text
def encrypt_text(text, key):
    fernet = Fernet(key)
    encoded_text = text.encode('utf-8')
    encrypted_text = fernet.encrypt(encoded_text)
    return encrypted_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encrypt', methods=['POST'])
def encrypt():
    key = generate_key()
    
    # Check if it's a file upload or text input
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_data = file.read()
        
        # Encrypt the file
        encrypted_data = encrypt_file(file_data, key)
        
        # Create response with encrypted file
        memory_file = io.BytesIO(encrypted_data)
        memory_file.seek(0)
        
        # Return the key and encrypted file
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f"encrypted_{filename}",
            mimetype='application/octet-stream'
        )
    
    elif 'text' in request.form and request.form['text'] != '':
        text = request.form['text']
        encrypted_text = encrypt_text(text, key)
        
        # Convert to base64 for display
        encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
        
        # Return the key and encrypted text
        return render_template('result.html', 
                              encrypted_text=encrypted_b64, 
                              key=key.decode('utf-8'))
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)