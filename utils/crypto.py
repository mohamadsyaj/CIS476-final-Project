import os
from cryptography.fernet import Fernet
import json

KEY_PATH = os.path.join(os.path.dirname(__file__), '..', 'secret.key')

def load_key():
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        return key
    with open(KEY_PATH, 'rb') as f:
        return f.read()

def _fernet():
    key = load_key()
    return Fernet(key)

def encrypt_json(obj):
    try:
        data = json.dumps(obj).encode('utf-8')
    except Exception:
        data = str(obj).encode('utf-8')
    return _fernet().encrypt(data).decode('utf-8')

def decrypt_json(token):
    if not token:
        return {}
    try:
        data = _fernet().decrypt(token.encode('utf-8'))
        return json.loads(data.decode('utf-8'))
    except Exception:
        return {}
