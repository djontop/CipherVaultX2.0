# CipherVaultX

A secure encryption and steganography application built with Flask.

## Environment Configuration

CipherVaultX now uses a `.env` file for configuration. This makes it easier to:
- Manage configuration in different environments
- Keep sensitive keys separate from code
- Customize the behavior of the application

### Available Configuration Options

| Variable | Description | Default Value |
|----------|-------------|---------------|
| USE_MESSAGE_FOR_PROMPT | Controls whether hidden messages are used to generate image prompts | true |
| DEFAULT_PROMPT_STYLE | Style for AI-generated prompts (artful, minimal, technical) | artful |
| SHOW_PROMPT_TO_USER | Whether to show the generated prompt to user in preview | true |
| IMAGE_MODEL | Hugging Face model to use for image generation | black-forest-labs/FLUX.1-dev |
| MAX_KEYWORDS_FROM_MESSAGE | Maximum keywords to extract from message for prompts | 5 |
| API_KEY | Hugging Face API key | (needs to be set) |
| DB_PATH | SQLite database path | cipher_stats.db |
| TEMP_STORAGE_TIMEOUT | Timeout in seconds for temporary file storage | 3600 |

### Setup

1. Copy the `.env.example` file to `.env`:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file to customize your configuration

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

## Features

- File and text encryption/decryption
- Image steganography (hide messages in images)
- AI-generated images for steganography
- Usage statistics 