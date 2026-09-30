import os
import json
import base64
import time
import random
import struct
from Crypto.Cipher import AES
from dotenv import load_dotenv

load_dotenv()

# Данные для создания Activity
activity = {
    "name": "Тест через curl",
    "idProject": 571,
    "idActivityType": 26,
    "idStatus": 1,
    "idActivityPlanningMode": 1,
    "creationDate": "2026-09-28"
}

# Шифрование (тот же алгоритм, что в projeqtor.py)
api_key = os.getenv('PJ_API_KEY')
aes_key_length = 128

key_bytes = api_key.encode('utf-8')
key_len = aes_key_length // 8
key_bytes = (key_bytes + b'\x00' * key_len)[:key_len]

ecb_cipher = AES.new(key_bytes, AES.MODE_ECB)
encrypted_key = b""
for i in range(0, len(key_bytes), 16):
    block = key_bytes[i:i+16]
    if len(block) < 16:
        block += b'\x00' * (16 - len(block))
    encrypted_key += ecb_cipher.encrypt(block)
final_key = encrypted_key[:key_len]

ms = int((time.time() * 1000) % 65536)
rnd = random.randint(0, 65535)
secs = int(time.time()) & 0xFFFFFFFF
nonce = struct.pack('>HHI', ms, rnd, secs)

ctr_cipher = AES.new(final_key, AES.MODE_CTR, nonce=nonce, initial_value=0)
ciphertext = ctr_cipher.encrypt(json.dumps(activity).encode('utf-8'))

encrypted_data = base64.b64encode(nonce + ciphertext).decode('utf-8')

# Генерация curl-команды
username = os.getenv('PJ_LOGIN')
password = os.getenv('PJ_PASSWORD')
base_url = os.getenv('PJ_URL').rstrip('/')

print("=" * 80)
print("Вариант 1: Через тело запроса (PUT)")
print("=" * 80)
curl_cmd_1 = f'''curl -X PUT "{base_url}/api/Activity" \\
  -u "{username}:{password}" \\
  -H "Content-Type: application/octet-stream" \\
  -d "{encrypted_data}" \\
  -v'''
print(curl_cmd_1)

print("\n" + "=" * 80)
print("Вариант 2: Через query string (POST)")
print("=" * 80)
curl_cmd_2 = f'''curl -X POST "{base_url}/api/Activity?uri=Activity&data={encrypted_data}" \\
  -u "{username}:{password}" \\
  -v'''
print(curl_cmd_2)

print("\n" + "=" * 80)
print("Исходные данные (JSON):")
print("=" * 80)
print(json.dumps(activity, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("Зашифрованные данные (Base64):")
print("=" * 80)
print(encrypted_data)