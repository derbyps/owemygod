"""Print a VAPID key pair for Web Push. Put both values in Render's environment.

Usage: python scripts/gen_vapid.py
"""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

key = ec.generate_private_key(ec.SECP256R1())
private = base64.urlsafe_b64encode(key.private_numbers().private_value.to_bytes(32, "big")).rstrip(b"=").decode()
public = base64.urlsafe_b64encode(key.public_key().public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)).rstrip(b"=").decode()
print(f"VAPID_PUBLIC_KEY={public}\nVAPID_PRIVATE_KEY={private}")
