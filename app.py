from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
import base64
import io
import time
import uuid
import secrets
from stegano import lsb
from PIL import Image
import requests
import re
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings from environment variables
def get_config(key, default=None):
    return os.environ.get(key, default)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dictionary to temporarily store encrypted files
encrypted_files = {}

# Dictionary to temporarily store decrypted files
decrypted_files = {}

# Dictionary to temporarily store AI preview images
ai_preview_images = {}

# Generate a secure token for temporary file access
def generate_download_token():
    return secrets.token_urlsafe(16)

# Store encrypted file temporarily with a token
def store_encrypted_file(data, filename):
    token = generate_download_token()
    encrypted_files[token] = {
        'data': data,
        'filename': filename,
        'timestamp': time.time()
    }
    return token

# Store decrypted file temporarily with a token
def store_decrypted_file(data, filename):
    token = generate_download_token()
    decrypted_files[token] = {
        'data': data,
        'filename': filename,
        'timestamp': time.time()
    }
    return token

# Cleanup function to remove old files from temp storage
def cleanup_old_files():
    current_time = time.time()
    timeout = int(get_config('TEMP_STORAGE_TIMEOUT', 3600))
    
    # Clean up encrypted files
    tokens_to_remove = []
    for token, file_info in encrypted_files.items():
        if current_time - file_info['timestamp'] > timeout:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del encrypted_files[token]
        
    # Clean up decrypted files
    tokens_to_remove = []
    for token, file_info in decrypted_files.items():
        if current_time - file_info['timestamp'] > timeout:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del decrypted_files[token]
        
    # Clean up AI preview images
    tokens_to_remove = []
    for token, image_info in ai_preview_images.items():
        if current_time - image_info['timestamp'] > timeout:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del ai_preview_images[token]

# Initialize database
def init_db():
    db_path = get_config('DB_PATH', 'cipher_stats.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS operation_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_type TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        file_size INTEGER,
        processing_time REAL,
        file_type TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database on startup
init_db()

# Function to log an operation
def log_operation(operation_type, file_size=None, processing_time=None, file_type=None):
    db_path = get_config('DB_PATH', 'cipher_stats.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO operation_stats (operation_type, timestamp, file_size, processing_time, file_type) VALUES (?, ?, ?, ?, ?)",
        (operation_type, datetime.now(), file_size, processing_time, file_type)
    )
    conn.commit()
    conn.close()

# Function to get operation statistics
def get_stats():
    db_path = get_config('DB_PATH', 'cipher_stats.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get counts by operation type
    cursor.execute("SELECT operation_type, COUNT(*) FROM operation_stats GROUP BY operation_type")
    counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get recent operations
    cursor.execute(
        "SELECT operation_type, timestamp, file_size, processing_time, file_type FROM operation_stats ORDER BY timestamp DESC LIMIT 10"
    )
    recent = cursor.fetchall()
    
    conn.close()
    
    return {
        'counts': counts,
        'recent': recent,
        'total': sum(counts.values())
    }

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
        else:
            # If no separator found but key is None, this is an error
            if key is None:
                raise Exception("No decryption key found. This may not be a direct encrypted text.")
    
    # Ensure key is not None before creating the Fernet instance
    if key is None:
        raise Exception("Decryption key is required and was not provided.")
    
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_text)
    return decrypted_data.decode('utf-8')

def hide_message_in_image(image_data, message):
    """Hide a message in an image using LSB steganography"""
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Save the image temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.png')
        image.save(temp_path)
        
        # Hide the message
        secret = lsb.hide(temp_path, message)
        
        # Save the result
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'stegano_output.png')
        secret.save(output_path)
        
        # Read the result
        with open(output_path, 'rb') as f:
            result_data = f.read()
        
        # Clean up temporary files
        os.remove(temp_path)
        os.remove(output_path)
        
        return result_data
    except Exception as e:
        raise Exception(f"Error hiding message: {str(e)}")

def reveal_message_from_image(image_data):
    """Extract hidden message from an image"""
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Save the image temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.png')
        image.save(temp_path)
        
        # Extract the message
        message = lsb.reveal(temp_path)
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return message
    except Exception as e:
        raise Exception(f"Error revealing message: {str(e)}")

def generate_prompt_from_message(message):
    """Generate an AI image prompt based on the hidden message content"""
    # Check if message-based prompt generation is enabled
    if get_config('USE_MESSAGE_FOR_PROMPT', 'true').lower() != 'true':
        return get_default_prompt()
    
    # Get a random default prompt if message is not suitable
    def get_default_prompt():
        default_prompts = [
            "A futuristic landscape where nature and technology coexist in harmony — lush green forests intertwined with glowing, transparent structures, solar trees absorbing sunlight, floating gardens in the sky, and bioluminescent plants lighting the pathways.",
            "An enchanted forest at twilight with luminescent mushrooms, fairy lights dancing between ancient trees, and a small cottage with a smoking chimney nestled among moss-covered stones.",
            "A cosmic scene showing the birth of a new galaxy, swirling nebulae in vibrant purples and blues, with stars being born in golden flashes against the vast darkness of space.",
            "An underwater city with crystal domes, bioluminescent architecture, and schools of colorful fish swimming through coral-lined streets, with rays of sunlight penetrating the water's surface.",
            "A floating steampunk city with brass and copper airships docked at towering spires, clockwork mechanisms turning massive gears, and steam rising from ornate pipework against a sunset sky.",
            "A tranquil Japanese garden in autumn, with red maple leaves falling onto a koi pond, stone lanterns casting warm light, and a small wooden bridge crossing gentle rippling waters.",
            "A mystical library with impossibly tall bookshelves that seem to extend infinitely, floating staircases, and books that emit soft glowing light as knowledge flows between them.",
            "A surreal dreamscape where objects defy gravity, doorways open to impossible places, and the sky shifts between day and night in patches, with crystalline structures reflecting prismatic light."
        ]
        return random.choice(default_prompts)
    
    # Clean and validate message
    if not message or len(message.strip()) < 5:
        return get_default_prompt()
    
    # Extract keywords (remove common words, punctuation)
    message = message.lower()
    
    # Remove common words and keep only meaningful keywords
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 
                   'about', 'as', 'of', 'is', 'was', 'were', 'be', 'been', 'being', 'am', 'are', 'have', 
                   'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could', 'should', 'i', 
                   'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
    
    # Remove special characters and split by spaces
    words = re.sub(r'[^\w\s]', '', message).split()
    
    # Filter out common words and short words
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    
    # If no good keywords, use default
    if not keywords:
        return get_default_prompt()
    
    # Take up to MAX_KEYWORDS_FROM_MESSAGE random keywords to build the prompt
    max_keywords = int(get_config('MAX_KEYWORDS_FROM_MESSAGE', 5))
    if len(keywords) > max_keywords:
        keywords = random.sample(keywords, max_keywords)
    
    # Adjust style based on configuration
    prompt_style = get_config('DEFAULT_PROMPT_STYLE', 'artful').lower()
    
    if prompt_style == 'minimal':
        # Simpler prompt style with minimal artistry
        prompt = "Image of "
        themes = [f"{keyword}" for keyword in keywords]
        prompt += ", ".join(themes)
        return prompt
        
    elif prompt_style == 'technical':
        # More technical/literal style
        prompt = "Technical illustration featuring "
        themes = [f"concept of {keyword}" for keyword in keywords]
        prompt += ", ".join(themes)
        return prompt
    
    else:  # artful (default)
        # Generate mood and style variations for artistic prompts
        moods = ['vibrant', 'mysterious', 'tranquil', 'dramatic', 'dreamy', 'surreal', 'fantastical', 'ethereal', 'dynamic', 'peaceful', 'chaotic', 'serene']
        styles = ['digital art', 'oil painting', 'watercolor', 'photorealistic', 'abstract', 'impressionist', 'cyberpunk', 'steampunk', 'fantasy', 'minimalist', 'concept art', 'ink drawing']
        
        # Create a prompt that doesn't directly reveal the message content
        prompt = f"A {random.choice(moods)} {random.choice(styles)} illustration featuring "
        
        # Add thematic elements based on keywords
        themes = []
        for keyword in keywords:
            theme_options = [
                f"symbolism of {keyword}",
                f"a {keyword}-inspired landscape",
                f"elements representing {keyword}",
                f"metaphorical representations of {keyword}",
                f"a scene centered around {keyword}",
                f"the concept of {keyword} reimagined",
                f"{keyword} transformed into visual poetry",
                f"the essence of {keyword} captured visually"
            ]
            themes.append(random.choice(theme_options))
        
        prompt += ", ".join(themes)
        
        return prompt

def generate_ai_image(prompt):
    """Generate an image using Hugging Face Stable Diffusion"""
    try:
        model = get_config('IMAGE_MODEL', 'black-forest-labs/FLUX.1-dev')
        api_key = get_config('API_KEY', '')
        
        API_URL = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Generate a random seed between 1 and 1,000,000
        random_seed = random.randint(1, 1000000)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "seed": random_seed,
                "guidance_scale": random.uniform(7.0, 8.5),  # Random guidance scale for style variation
                "num_inference_steps": random.randint(30, 50)  # Random number of steps for detail variation
            }
        }
        
        # Log the parameters for debugging
        print(f"Image generation parameters: seed={random_seed}, prompt='{prompt}'")
        
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
            
        return response.content
    except Exception as e:
        raise Exception(f"Error generating image: {str(e)}")

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
    file_size = len(file_data)
    file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
    start_time = time.time()  # Start timing

    try:
        if use_key:
            # Ensure we have a key - if user didn't provide one, generate a new one
            key_input = request.form.get('key', '').strip()
            if key_input:
                key = key_input.encode('utf-8')
            else:
                key = generate_key()
                
            encrypted_data, _ = encrypt_file(file_data, key, use_key=True)
        else:
            encrypted_data, key = encrypt_file(file_data, use_key=False)

        # Store encrypted data temporarily and get token
        download_filename = f"encrypted_{filename}"
        token = store_encrypted_file(encrypted_data, download_filename)

        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Encryption Time: {time_taken:.2f} ms")  # Print to console

        # Log the operation
        log_operation('file_encryption', file_size=file_size, processing_time=time_taken, file_type=file_type)
        
        # Clean up old files
        cleanup_old_files()
        
        # Render the file result page
        return render_template('file_result.html', 
                              key=key.decode('utf-8'), 
                              filename=download_filename,
                              token=token,
                              use_key=use_key)

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
    file_size = len(file_data)
    file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
    
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

        # Log the operation
        log_operation('file_decryption', file_size=file_size, processing_time=time_taken, file_type=file_type)
        
        # Store decrypted data temporarily and get token
        download_filename = f"decrypted_{original_filename}"
        token = store_decrypted_file(decrypted_data, download_filename)
        
        # Clean up old files
        cleanup_old_files()
        
        # Render the file result page
        return render_template('file_decrypt_result.html', 
                              filename=download_filename,
                              token=token)

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/encrypt_text', methods=['POST'])
def encrypt_text_route():
    use_key = request.form.get('use_key') == 'true'
    
    if 'text' not in request.form or not request.form['text'].strip():
        return redirect(url_for('index'))
    
    text = request.form['text'].strip()
    text_size = len(text.encode('utf-8'))
    start_time = time.time()  # Start timing

    try:
        if use_key:
            # Ensure we have a key - if user didn't provide one, generate a new one
            key_input = request.form.get('key', '').strip()
            if key_input:
                key = key_input.encode('utf-8')
            else:
                key = generate_key()
                
            encrypted_text, _ = encrypt_text(text, key, use_key=True)
        else:
            key = generate_key()
            encrypted_text, _ = encrypt_text(text, key, use_key=False)

        encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Text Encryption Time: {time_taken:.2f} ms")  # Print to console
        
        # Log the operation
        log_operation('text_encryption', file_size=text_size, processing_time=time_taken, file_type='text')

        return render_template('result.html', encrypted_text=encrypted_b64, key=key.decode('utf-8'))
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/decrypt_text', methods=['POST'])
def decrypt_text_route():
    use_key = request.form.get('use_key') == 'true'

    if 'text' not in request.form or not request.form['text'].strip():
        return render_template('error.html', error="Encrypted text is required.")

    encrypted_b64 = request.form['text'].strip()
    text_size = len(encrypted_b64)
    start_time = time.time()  # Start timing

    try:
        # First try to decode the base64 content
        try:
            encrypted_text = base64.b64decode(encrypted_b64)
        except Exception:
            return render_template('error.html', error="Invalid encrypted text format. Please paste the entire encrypted text.")
        
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
        else:
            # For direct decryption, we don't need a separate key as it should be included in the encrypted data
            # Check if the text contains our separator
            if b"||KEY_SEPARATOR||" not in encrypted_text:
                return render_template('error.html', error="This doesn't appear to be a directly encrypted text. Try the 'Text + Key' option instead.")
            key = None  # The decrypt_text function will extract the key if it's embedded

        decrypted_text = decrypt_text(encrypted_text, key)
        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Text Decryption Time: {time_taken:.2f} ms")  # Print to console
        
        # Log the operation
        log_operation('text_decryption', file_size=text_size, processing_time=time_taken, file_type='text')

        return render_template('decrypt_result.html', decrypted_text=decrypted_text)

    except Exception as e:
        error_msg = str(e)
        if "No decryption key found" in error_msg:
            error_msg = "This text requires a key for decryption. Try using the 'Text + Key' option."
        elif "Decryption key is required" in error_msg:
            error_msg = "A decryption key is required. Please provide a valid key."
        elif "Invalid token" in error_msg:
            error_msg = "Invalid encryption key or corrupted encrypted text."
        
        return render_template('error.html', error=f"Decryption failed: {error_msg}")

@app.route('/steganography')
def steganography():
    return render_template('index.html', active_tab='steganography')

@app.route('/hide_message', methods=['POST'])
def hide_message():
    use_ai = request.form.get('use_ai') == 'true'
    
    if 'message' not in request.form or not request.form['message'].strip():
        return render_template('error.html', error="No message provided")
    
    message = request.form['message'].strip()
    message_size = len(message.encode('utf-8'))
    
    try:
        start_time = time.time()
        
        # Handle AI-generated image
        if use_ai:
            # First check if we have a preview token
            preview_token = request.form.get('preview_token', '').strip()
            
            if preview_token and preview_token in ai_preview_images:
                # Use the previously generated preview image if available
                image_info = ai_preview_images[preview_token]
                image_data = image_info['data']
                # Remove from storage to free memory
                del ai_preview_images[preview_token]
                file_type = 'ai_image_png'
            else:
                # No preview image available, generate a new one
                user_prompt = request.form.get('prompt', '').strip()
                
                if user_prompt:
                    # Use user's custom prompt if provided
                    prompt = user_prompt
                else:
                    # Generate a prompt based on the message content or default
                    prompt = generate_prompt_from_message(message)
                    
                # Log the generated prompt (for debugging)
                print(f"Using prompt: {prompt}")
                
                # Generate the image
                image_data = generate_ai_image(prompt)
                file_type = 'ai_image_png'
        # Handle uploaded image
        else:
            if 'image' not in request.files or request.files['image'].filename == '':
                return render_template('error.html', error="No image file selected")
            
            image = request.files['image']
            filename = secure_filename(image.filename)
            file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
            image_data = image.read()
        
        # Hide message in the image
        stegano_image = hide_message_in_image(image_data, message)
        
        end_time = time.time()
        time_taken = (end_time - start_time) * 1000
        
        # Log the operation
        log_operation('steganography_hide', file_size=message_size, processing_time=time_taken, file_type=file_type)
        
        memory_file = io.BytesIO(stegano_image)
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            as_attachment=True,
            download_name="stegano_image.png",
            mimetype='image/png'
        )
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/reveal_message', methods=['POST'])
def reveal_message():
    if 'image' not in request.files or request.files['image'].filename == '':
        return render_template('error.html', error="No image file selected")
    
    image = request.files['image']
    filename = secure_filename(image.filename)
    file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
    file_size = 0
    
    try:
        start_time = time.time()
        
        image_data = image.read()
        file_size = len(image_data)
        message = reveal_message_from_image(image_data)
        
        end_time = time.time()
        time_taken = (end_time - start_time) * 1000
        
        # Log the operation
        log_operation('steganography_reveal', file_size=file_size, processing_time=time_taken, file_type=file_type)
        
        return render_template('decrypt_result.html', decrypted_text=message, type="steganography")
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/generate_image', methods=['POST'])
def generate_image_route():
    prompt = request.form.get('prompt', '').strip()
    message = request.form.get('message', '').strip()
    
    # If prompt is empty, generate from message or use default
    if not prompt:
        if message and get_config('USE_MESSAGE_FOR_PROMPT', 'true').lower() == 'true':
            prompt = generate_prompt_from_message(message)
        else:
            # Use a random default prompt
            def get_default_prompt():
                default_prompts = [
                    "A futuristic landscape where nature and technology coexist in harmony",
                    "An enchanted forest at twilight with luminescent mushrooms",
                    "A cosmic scene showing the birth of a new galaxy",
                    "An underwater city with crystal domes and bioluminescent architecture",
                    "A floating steampunk city with brass and copper airships",
                    "A tranquil Japanese garden in autumn with maple leaves falling",
                    "A mystical library with impossibly tall bookshelves",
                    "A surreal dreamscape where objects defy gravity"
                ]
                return random.choice(default_prompts)
            
            prompt = get_default_prompt()
    
    try:
        image_data = generate_ai_image(prompt)
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Store the generated image with a token
        preview_token = secrets.token_urlsafe(16)
        ai_preview_images[preview_token] = {
            'data': image_data,
            'prompt': prompt,
            'timestamp': time.time()
        }
        
        # Determine whether to show the prompt to the user
        show_prompt = get_config('SHOW_PROMPT_TO_USER', 'true').lower() == 'true'
        
        return jsonify({
            'success': True, 
            'image': f"data:image/png;base64,{image_b64}",
            'prompt': prompt if show_prompt else None,
            'preview_token': preview_token
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stats')
def statistics():
    """Display statistics about the application usage"""
    stats = get_stats()
    
    # Format timestamps for display
    if 'recent' in stats:
        formatted_recent = []
        for op in stats['recent']:
            # Format: operation_type, timestamp, file_size, processing_time, file_type
            op_type = op[0]
            
            # Parse timestamp string to datetime object
            if isinstance(op[1], str):
                try:
                    timestamp = datetime.strptime(op[1], '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    timestamp = datetime.strptime(op[1], '%Y-%m-%d %H:%M:%S')
            else:
                timestamp = op[1]
                
            formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Format file size
            file_size = op[2]
            if file_size:
                if file_size > 1048576:  # 1 MB
                    formatted_size = f"{file_size/1048576:.2f} MB"
                else:
                    formatted_size = f"{file_size/1024:.2f} KB"
            else:
                formatted_size = "N/A"
                
            # Format processing time
            proc_time = op[3]
            if proc_time:
                if proc_time > 1000:  # 1 second
                    formatted_proc_time = f"{proc_time/1000:.2f} s"
                else:
                    formatted_proc_time = f"{proc_time:.2f} ms"
            else:
                formatted_proc_time = "N/A"
                
            file_type = op[4] or "N/A"
            
            formatted_recent.append((op_type, formatted_time, formatted_size, formatted_proc_time, file_type))
        
        stats['recent'] = formatted_recent
    
    return render_template('stats.html', stats=stats)

@app.route('/stats-data')
def stats_data():
    """Return statistics data in JSON format for AJAX usage"""
    stats = get_stats()
    return jsonify(stats)

@app.route('/download-encrypted-file/<token>')
def download_encrypted_file(token):
    # Verify token and get file info
    if token not in encrypted_files:
        return render_template('error.html', error="File not found or has expired. Please encrypt your file again.")
    
    file_info = encrypted_files[token]
    encrypted_data = file_info['data']
    filename = file_info['filename']
    
    # Create a BytesIO object for the file
    memory_file = io.BytesIO(encrypted_data)
    memory_file.seek(0)
    
    # Send the file to the user
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

@app.route('/download-decrypted-file/<token>')
def download_decrypted_file(token):
    # Verify token and get file info
    if token not in decrypted_files:
        return render_template('error.html', error="File not found or has expired. Please decrypt your file again.")
    
    file_info = decrypted_files[token]
    decrypted_data = file_info['data']
    filename = file_info['filename']
    
    # Create a BytesIO object for the file
    memory_file = io.BytesIO(decrypted_data)
    memory_file.seek(0)
    
    # Send the file to the user
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
