# app/lib/secrets.py
import os
import sys
import json
import base64
import httpx
from typing import Dict, Optional, Any
from pydantic import BaseModel

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# ============================================================
# SYMMETRIC ENCRYPTION FOR ENVIRONMENT VARIABLES
# ============================================================

class EncryptedSecret(BaseModel):
    encrypted: str
    iv: str
    auth_tag: str

def encrypt_secret(plaintext: str, key_base64: str) -> EncryptedSecret:
    """
    Encrypts a plaintext secret using AES-256-GCM.
    
    Args:
        plaintext: The secret to encrypt
        key_base64: Base64-encoded 32-byte key for AES-256
    """
    # FIX SEC-001: Validate the key_base64 parameter, not env var
    if not key_base64:
        raise ValueError("key_base64 parameter is required for encryption")

    try:
        key_buffer = base64.b64decode(key_base64)
        if len(key_buffer) != 32:
            raise ValueError("key_base64 must decode to 32 bytes (256 bits)")

        iv = os.urandom(16)  # 16 bytes for GCM

        cipher = Cipher(
            algorithms.AES(key_buffer),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()

        encrypted_bytes = cipher.update(plaintext.encode('utf-8')) + cipher.finalize()
        auth_tag = cipher.tag

        return EncryptedSecret(
            encrypted=base64.b64encode(encrypted_bytes).decode('utf-8'),
            iv=base64.b64encode(iv).decode('utf-8'),
            auth_tag=base64.b64encode(auth_tag).decode('utf-8')
        )
    except Exception as e:
        print(f"[Secrets] Encryption failed: {e}", file=sys.stderr)
        raise

def decrypt_secret(encrypted_secret: EncryptedSecret, key_base64: str) -> str:
    """
    Decrypts an AES-256-GCM encrypted secret.
    """
    try:
        key_buffer = base64.b64decode(key_base64)
        if len(key_buffer) != 32:
            raise ValueError("ENCRYPTION_KEY must be 32 bytes (256 bits)")

        iv = base64.b64decode(encrypted_secret.iv)
        encrypted_bytes = base64.b64decode(encrypted_secret.encrypted)
        auth_tag = base64.b64decode(encrypted_secret.auth_tag)

        decipher = Cipher(
            algorithms.AES(key_buffer),
            modes.GCM(iv, auth_tag),
            backend=default_backend()
        ).decryptor()

        decrypted_bytes = decipher.update(encrypted_bytes) + decipher.finalize()
        
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"[Secrets] Decryption failed: {e}", file=sys.stderr)
        raise

# ============================================================
# HASHICORP VAULT INTEGRATION
# ============================================================

VAULT_URL = os.getenv("VAULT_URL", "")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")

async def fetch_vault_secret(vault_url: str, token: str, secret_path: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single secret from Vault using its v1 kv API.
    """
    headers = {"X-Vault-Token": token}
    url = f"{vault_url.rstrip('/')}/v1/{secret_path.lstrip('/')}"
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, timeout=10.0)
            res.raise_for_status()
            
            data = res.json()
            # Vault v2 kv returns data in data.data.value
            if data and "data" in data and "data" in data["data"]:
                return data["data"]["data"]
            # Vault v1 kv returns data in data.data
            elif data and "data" in data:
                return data["data"]
        return None
    except Exception as e:
        print(f"[Vault] failed to fetch secret {secret_path}: {e}", file=sys.stderr)
        return None

async def load_secrets_from_vault(mapping: Dict[str, str]):
    """
    Load a mapping of env names to Vault secret paths
    and set os.environ values when found.
    """
    if not VAULT_URL or not VAULT_TOKEN:
        print("[Secrets] Vault not configured (VAULT_URL/VAULT_TOKEN missing). Skipping.")
        return

    for env_key, secret_path in mapping.items():
        try:
            data = await fetch_vault_secret(VAULT_URL, VAULT_TOKEN, secret_path)
            if data and isinstance(data, dict):
                if "value" in data and isinstance(data["value"], str) and len(data) == 1:
                    os.environ[env_key] = data["value"]
                else:
                    os.environ[env_key] = json.dumps(data)
                
                print(f"[Secrets] Loaded {env_key} from Vault path {secret_path}")
            
        except Exception as e:
            print(f"[Secrets] Failed to load {env_key} from {secret_path}: {e}", file=sys.stderr)
