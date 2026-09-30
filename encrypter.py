import json
import httpx
from dotenv import load_dotenv
import os
import re

import base64
import time
import random
import struct
from Crypto.Cipher import AES

def encrypt_data(api_key, json_str: str):
        """
        Шифрование данных по спецификации ProjeQtOr (AES-CTR).
        Совместимо с src/external/phpAES/aesctr.class.php
        """
        # 1. Подготовка ключа (добавляем нули или обрезаем до нужной длины)
        key_bytes = api_key.encode('utf-8')
        aes_key_length = 128
        key_len = aes_key_length // 8
        key_bytes = (key_bytes + b'\x00' * key_len)[:key_len]
        
        # 2. Key schedule: ключ шифруется самим собой в режиме ECB
        ecb_cipher = AES.new(key_bytes, AES.MODE_ECB)
        encrypted_key = b""
        for i in range(0, len(key_bytes), 16):
            block = key_bytes[i:i+16]
            if len(block) < 16:
                block += b'\x00' * (16 - len(block))
            encrypted_key += ecb_cipher.encrypt(block)
        final_key = encrypted_key[:key_len]
        
        # 3. Генерация Nonce (8 байт)
        # [0-1] миллисекунды, [2-3] случайное число, [4-7] секунды от epoch
        ms = int((time.time() * 1000) % 65536)
        rnd = random.randint(0, 65535)
        secs = int(time.time()) & 0xFFFFFFFF
        nonce = struct.pack('>HHI', ms, rnd, secs)
        
        # 4. Шифрование AES-CTR (8 байт nonce, 8 байт счетчик)
        ctr_cipher = AES.new(final_key, AES.MODE_CTR, nonce=nonce, initial_value=0)
        ciphertext = ctr_cipher.encrypt(json_str.encode('utf-8'))
        
        # 5. Добавление nonce в начало и кодирование в Base64
        return base64.b64encode(nonce + ciphertext).decode('utf-8')


api_key = 'b7068c9cd44b18947ce66a6a2a0d0482'
json_str = '{"name": "Тест", "idProject": 571}'

print(encrypt_data(api_key, json_str))