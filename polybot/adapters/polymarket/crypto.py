from __future__ import annotations

import hashlib


def is_valid_private_key(pk: str) -> bool:
    if not isinstance(pk, str):
        return False
    if not pk.startswith("0x"):
        return False
    hexpart = pk[2:]
    if len(hexpart) != 64:
        return False
    try:
        int(hexpart, 16)
        return True
    except ValueError:
        return False


def derive_address_like(pk: str) -> str:
    """Derive a deterministic address-like string from a private key for validation/logging.

    Note: This is NOT a real Ethereum address derivation. It's a keccak/sha-based placeholder
    for non-sensitive diagnostics. Do NOT use for signing.
    """
    if not is_valid_private_key(pk):
        raise ValueError("invalid private key")
    # Simple derivation: sha256 of hex bytes -> last 20 bytes
    data = bytes.fromhex(pk[2:])
    h = hashlib.sha256(data).digest()
    addr = h[-20:]
    return "0x" + addr.hex()

