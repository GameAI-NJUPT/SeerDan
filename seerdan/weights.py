import hashlib
import io

_P0 = bytes.fromhex(
    "d5931b7f44e9dc5f77fc30e4f8d413e9555748acf02f114c21cc8efccb8e6edc7a87b26f74888816")
_P1 = bytes.fromhex(
    "96ef71eac55d37b6d3538ee5cf486bd72f0aaeff9f2bf1997e5684248c7c94c2803cfabd0f6df944")
_S = bytes.fromhex(
    "1a02a13da0e261ce9ad0f91bbb1af59bea8d740e670c1b90")

_MAGIC = b"SDW2"
_AAD = b"seerdan-policy-v1"


def _key():
    material = bytes(_P0[i] ^ ((_P1[i] + ((i * 13 + 7) & 0xFF)) & 0xFF)
                     for i in range(40))
    return hashlib.sha256(_S + material + _S[::-1]).digest()


def load_policy(path, device="cpu"):

    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:4] != _MAGIC:
        raise ValueError("%s is not a SeerDan weight archive" % path)
    nonce, payload = blob[4:16], blob[16:]
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    plain = AESGCM(_key()).decrypt(nonce, payload, _AAD)
    import torch
    model = torch.jit.load(io.BytesIO(plain), map_location=device)
    model.eval()
    return model
