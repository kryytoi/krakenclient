"""
Шифрует KrakenClient.jar -> KrakenClient.enc перед публикацией релиза на GitHub.

Использование:
    python encrypt_build.py KrakenClient.jar KrakenClient.enc

Если переменной окружения KRAKEN_ENC_KEY_B64 нет — сгенерирует новый ключ
и выведет его. Этот же ключ нужно положить в переменные окружения сайта
(Vercel -> Settings -> Environment Variables -> KRAKEN_ENC_KEY_B64).

Формат .enc файла: [16 байт IV][AES-256-CBC шифротекст с PKCS7-паддингом]
"""
import base64
import os
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


def encrypt(in_path, out_path, key: bytes):
    iv = os.urandom(16)
    with open(in_path, "rb") as f:
        raw = f.read()

    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()

    with open(out_path, "wb") as f:
        f.write(iv + ct)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python encrypt_build.py <вход.jar> <выход.enc>")
        sys.exit(1)

    key_b64 = os.environ.get("KRAKEN_ENC_KEY_B64")
    if not key_b64:
        key = os.urandom(32)
        key_b64 = base64.b64encode(key).decode()
        print("Сгенерирован новый ключ, сохраните его в переменные окружения сайта:")
        print("KRAKEN_ENC_KEY_B64 =", key_b64)
    else:
        key = base64.b64decode(key_b64)

    encrypt(sys.argv[1], sys.argv[2], key)
    print(f"Готово: {sys.argv[2]}")
