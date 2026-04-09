import os

def sanitize_css():
    path = 'style.css'
    if not os.path.exists(path):
        print("style.css not found")
        return

    # Read binary content
    with open(path, 'rb') as f:
        content = f.read()

    # Remove UTF-16 BOMs (0xFF 0xFE) which might be scattered
    # Also remove null bytes if the file was interpreted as single-byte
    clean_bytes = content.replace(b'\xff\xfe', b'')
    
    # Attempt to decode
    # If the file was UTF-16, it will have null bytes between characters
    # If it's a mix, we need to be careful.
    
    try:
        # Try decoding as UTF-16 first
        text = content.decode('utf-16')
    except:
        try:
            # Fallback to UTF-8
            text = content.decode('utf-8')
        except:
            # Last resort: latin-1 and manual cleanup
            text = content.decode('latin-1').replace('\x00', '').replace('ÿþ', '')

    # Write back as clean UTF-8
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print("style.css sanitized and saved as UTF-8")

sanitize_css()
