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

load_dotenv()

class Projeqtor:

    def __init__(self):
        self.base_url = os.getenv('PJ_URL').rstrip('/')
        self.username = os.getenv('PJ_LOGIN')  
        self.password = os.getenv('PJ_PASSWORD')
        self.api_key = os.getenv('PJ_API_KEY')
        self.aes_key_length = 128

    def _encrypt_data(self, json_str: str) -> str:
        """
        Шифрование данных по спецификации ProjeQtOr (AES-CTR).
        Совместимо с src/external/phpAES/aesctr.class.php
        """
        # 1. Подготовка ключа (добавляем нули или обрезаем до нужной длины)
        key_bytes = self.api_key.encode('utf-8')
        key_len = self.aes_key_length // 8
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

    def post_activity(self, activity_data: dict):
        url = f"{self.base_url}/api/Activity"
        
        # Сериализация и шифрование
        json_payload = json.dumps(activity_data, ensure_ascii=False)
        encrypted_data = self._encrypt_data(json_payload)
        
        with httpx.Client(
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-httpx",
                "Content-Type": "application/octet-stream" 
            },
            auth=httpx.BasicAuth(username=self.username, password=self.password),
            timeout=15.0
        ) as client:
            # ПЕРЕДАЧА ДАННЫХ В ТЕЛЕ ЗАПРОСА (надёжнее для POST)
            response = client.post(url, content=encrypted_data)
            
            # Защита от HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                raise RuntimeError(
                    "Сервер вернул HTML вместо JSON. "
                    "Проверьте, включен ли API и настроен ли .htaccess в папке /api/."
                )
            
            response.raise_for_status()
            
            return self._safe_json_parse(response)
    
    def _safe_json_parse(self, response):
        """Парсинг JSON с обработкой багов ProjeQtOr."""
        text = response.text.lstrip('\ufeff')
        
        # Ищем начало JSON
        start = text.find('{')
        if start == -1:
            raise ValueError(f"JSON не найден в ответе. Начало: {text[:200]}")
        
        clean_text = text[start:]
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            # Пытаемся исправить неэкранированные кавычки в значениях
            # Простая эвристика: заменяем "" на \" внутри message
            import re
            fixed = re.sub(r'"message":""([^"]*)"', r'"message":"\1"', clean_text)
            try:
                return json.loads(fixed)
            except:
                raise ValueError(
                    f"Невалидный JSON. Позиция: {e.pos}. "
                    f"Контекст: {repr(clean_text[max(0, e.pos-30):e.pos+30])}"
                )
