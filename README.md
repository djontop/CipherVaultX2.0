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
| AI_PROVIDER | AI service to use for image generation (huggingface, openai) | huggingface |
| HF_IMAGE_MODEL | Hugging Face model for image generation | black-forest-labs/FLUX.1-dev |
| HF_API_KEY | Hugging Face API key | (needs to be set) |
| OPENAI_IMAGE_MODEL | OpenAI DALL-E model version (dall-e-3, dall-e-2) | dall-e-3 |
| OPENAI_API_KEY | OpenAI API key | (needs to be set) |
| OPENAI_IMAGE_QUALITY | Quality setting for DALL-E 3 (standard, hd) | standard |
| OPENAI_IMAGE_SIZE | Size of generated images | 1024x1024 |
| MAX_KEYWORDS_FROM_MESSAGE | Maximum keywords to extract from message for prompts | 5 |
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
- AI-generated images for steganography using:
  - Hugging Face's Stable Diffusion models
  - OpenAI's DALL-E models
- Usage statistics

## AI Image Generation

CipherVaultX supports two providers for AI image generation:

### Hugging Face
- Uses various open-source Stable Diffusion models
- Default model: black-forest-labs/FLUX.1-dev
- Requires a Hugging Face API key

### OpenAI DALL-E
- Supports both DALL-E 2 and DALL-E 3 models
- Produces high-quality, realistic images
- Requires an OpenAI API key
- Uses OpenAI API v0.28.0
- Various quality and size options available

You can select your preferred provider in the user interface or by setting the `AI_PROVIDER` environment variable. 