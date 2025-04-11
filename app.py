from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
import base64
import io
import time
from stegano import lsb
from PIL import Image
import requests
import re
import random

CONFIG = {
    'USE_MESSAGE_FOR_PROMPT': False,
    'DEFAULT_PROMPT_STYLE': 'artful',
    'SHOW_PROMPT_TO_USER': True,
    'IMAGE_MODEL': 'runwayml/stable-diffusion-v1-5',
    'MAX_KEYWORDS_FROM_MESSAGE': 5,
    'API_KEY': 'hf_YwTyWIybPuOKIstc',
}

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

def decrypt_text(encrypted_text, key=None):

    if key is None or b"||KEY_SEPARATOR||" in encrypted_text:

        parts = encrypted_text.split(b"||KEY_SEPARATOR||", 1)
        if len(parts) == 2:
            key = parts[0]
            encrypted_text = parts[1]
    
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_text)
    return decrypted_data.decode('utf-8')

def hide_message_in_image(image_data, message):
    """Hide a message in an image using LSB steganography"""
    try:
        image = Image.open(io.BytesIO(image_data))
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.png')
        image.save(temp_path)
        secret = lsb.hide(temp_path, message)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'stegano_output.png')
        secret.save(output_path)
        with open(output_path, 'rb') as f:
            result_data = f.read()
        os.remove(temp_path)
        os.remove(output_path)
        
        return result_data
    except Exception as e:
        raise Exception(f"Error hiding message: {str(e)}")

def reveal_message_from_image(image_data):
    """Extract hidden message from an image"""
    try:
        image = Image.open(io.BytesIO(image_data))
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.png')
        image.save(temp_path)
        message = lsb.reveal(temp_path)
        os.remove(temp_path)
        
        return message
    except Exception as e:
        raise Exception(f"Error revealing message: {str(e)}")

def generate_prompt_from_message(message):
    """Generate an AI image prompt based on the hidden message content"""
    if not CONFIG['USE_MESSAGE_FOR_PROMPT']:
        return get_default_prompt()
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
    if not message or len(message.strip()) < 5:
        return get_default_prompt()
    message = message.lower()
    
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 
                   'about', 'as', 'of', 'is', 'was', 'were', 'be', 'been', 'being', 'am', 'are', 'have', 
                   'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could', 'should', 'i', 
                   'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}

    words = re.sub(r'[^\w\s]', '', message).split()
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    if not keywords:
        return get_default_prompt()
    max_keywords = CONFIG['MAX_KEYWORDS_FROM_MESSAGE']
    if len(keywords) > max_keywords:
        keywords = random.sample(keywords, max_keywords)
    prompt_style = CONFIG['DEFAULT_PROMPT_STYLE'].lower()
    
    if prompt_style == 'minimal':
        prompt = "Image of "
        themes = [f"{keyword}" for keyword in keywords]
        prompt += ", ".join(themes)
        return prompt
        
    elif prompt_style == 'technical':
        prompt = "Technical illustration featuring "
        themes = [f"concept of {keyword}" for keyword in keywords]
        prompt += ", ".join(themes)
        return prompt
    
    else:
        moods = ['vibrant', 'mysterious', 'tranquil', 'dramatic', 'dreamy', 'surreal', 'fantastical', 'ethereal', 'dynamic', 'peaceful', 'chaotic', 'serene']
        styles = ['digital art', 'oil painting', 'watercolor', 'photorealistic', 'abstract', 'impressionist', 'cyberpunk', 'steampunk', 'fantasy', 'minimalist', 'concept art', 'ink drawing']
        prompt = f"A {random.choice(moods)} {random.choice(styles)} illustration featuring "
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
        API_URL = f"https://api-inference.huggingface.co/models/{CONFIG['IMAGE_MODEL']}"
        headers = {"Authorization": f"Bearer {CONFIG['API_KEY']}"}
        random_seed = random.randint(1, 1000000)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "seed": random_seed,
                "guidance_scale": random.uniform(7.0, 8.5),
                "num_inference_steps": random.randint(30, 50)
            }
        }
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
    start_time = time.time()

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
            encrypted_data, _ = encrypt_file(file_data, key, use_key=True)
        else:
            encrypted_data, key = encrypt_file(file_data, use_key=False)

        end_time = time.time()  # End timing
        time_taken = (end_time - start_time) * 1000
        print(f"Encryption Time: {time_taken:.2f} ms")
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
    
    start_time = time.time()

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            decrypted_data = decrypt_file(file_data, key)
        else:
            decrypted_data = decrypt_file(file_data)

        end_time = time.time()
        time_taken = (end_time - start_time) * 1000
        print(f"Decryption Time: {time_taken:.2f} ms")

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
    start_time = time.time()

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8') or generate_key()
        else:
            key = generate_key()

        encrypted_text, _ = encrypt_text(text, key)
        encrypted_b64 = base64.b64encode(encrypted_text).decode('utf-8')
        end_time = time.time()
        time_taken = (end_time - start_time) * 1000
        print(f"Text Encryption Time: {time_taken:.2f} ms")

        return render_template('result.html', encrypted_text=encrypted_b64, key=key.decode('utf-8'))
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/decrypt_text', methods=['POST'])
def decrypt_text_route():
    use_key = request.form.get('use_key') == 'true'

    if 'text' not in request.form or not request.form['text'].strip():
        return render_template('error.html', error="Encrypted text is required.")

    encrypted_b64 = request.form['text'].strip()
    start_time = time.time()

    try:
        if use_key:
            key = request.form.get('key', '').strip().encode('utf-8')
            if not key:
                return render_template('error.html', error="Decryption key is required.")
            encrypted_text = base64.b64decode(encrypted_b64)
        else:
            return render_template('error.html', error="Decryption key is required.")

        decrypted_text = decrypt_text(encrypted_text, key)
        end_time = time.time()
        time_taken = (end_time - start_time) * 1000
        print(f"Text Decryption Time: {time_taken:.2f} ms")

        return render_template('decrypt_result.html', decrypted_text=decrypted_text)

    except Exception as e:
        return render_template('error.html', error=f"Decryption failed: {str(e)}")

@app.route('/steganography')
def steganography():
    return render_template('index.html', active_tab='steganography')

@app.route('/hide_message', methods=['POST'])
def hide_message():
    use_ai = request.form.get('use_ai') == 'true'
    
    if 'message' not in request.form or not request.form['message'].strip():
        return render_template('error.html', error="No message provided")
    message = request.form['message'].strip()
    
    try:
        if use_ai:
            user_prompt = request.form.get('prompt', '').strip()
            
            if user_prompt:
                prompt = user_prompt
            else:
                prompt = generate_prompt_from_message(message)
            print(f"Using prompt: {prompt}")
            image_data = generate_ai_image(prompt)
        else:
            if 'image' not in request.files or request.files['image'].filename == '':
                return render_template('error.html', error="No image file selected")
            
            image = request.files['image']
            image_data = image.read()
        stegano_image = hide_message_in_image(image_data, message)
        
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
    
    try:
        image_data = image.read()
        message = reveal_message_from_image(image_data)
        
        return render_template('decrypt_result.html', decrypted_text=message, type="steganography")
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/generate_image', methods=['POST'])
def generate_image_route():
    prompt = request.form.get('prompt', '').strip()
    message = request.form.get('message', '').strip()
    if not prompt:
        if message and CONFIG['USE_MESSAGE_FOR_PROMPT']:
            prompt = generate_prompt_from_message(message)
        else:
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
        show_prompt = CONFIG['SHOW_PROMPT_TO_USER']
        return jsonify({
            'success': True, 
            'image': f"data:image/png;base64,{image_b64}",
            'prompt': prompt if show_prompt else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
