import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('GOOGLE_OAUTH_ACCESS_TOKEN')
url = 'https://us-central1-aiplatform.googleapis.com/v1/projects/rag-agent-490801/locations/us-central1/reasoningEngines/7507846375233552384:streamQuery'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

payload = {
    'class_method': 'stream_query',
    'input': {
        'message': 'Olá! O que você pode me dizer sobre a estrutura organizacional da Prowise?',
        'user_id': 'test_user'
    }
}

print(f"Sending request to: {url}")
response = requests.post(url, headers=headers, json=payload, stream=True)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
else:
    print("Response stream:")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            print(decoded_line)
