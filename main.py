import os
import json
import requests
from bs4 import BeautifulSoup

# Переменные окружения
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
DOCUMENT_ID = os.getenv("DOCUMENT_ID")
# Теперь нам нужен только токен доступа (его можно получить через сервис-аккаунт вручную или библиотеку google-auth)
# Но для максимальной экономии RAM лучше использовать легкую google-auth вместо всего SDK
from google.oauth2 import service_account
import google.auth.transport.requests

def get_access_token():
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/documents']
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def clear_and_update():
    token = get_access_token()
    headers_auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = f"https://docs.googleapis.com/v1/documents/{DOCUMENT_ID}"

    # 1. Получаем документ (только структуру для endIndex)
    doc_resp = requests.get(base_url, headers=headers_auth).json()
    end_index = doc_resp.get('body').get('content')[-1].get('endIndex')

    requests_list = []
    if end_index > 2:
        requests_list.append({
            'deleteContentRange': {
                'range': {'startIndex': 1, 'endIndex': end_index - 1}
            }
        })

    # 2. Парсинг (используем lxml для экономии памяти)
    url = f"https://t.me/s/{CHANNEL_NAME}"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    # Указываем 'lxml', он потребляет меньше памяти чем 'html.parser'
    soup = BeautifulSoup(response.text, 'lxml') 
    
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    all_text = ""
    for msg in messages:
        text = msg.get_text(separator='\n').strip()
        all_text += f"{text}\n{'-'*20}\n\n"

    if not all_text:
        all_text = "Текстовых сообщений не обнаружено."

    # Освобождаем память от тяжелых объектов парсинга явно
    del soup
    del response

    # 3. Обновление через прямой POST запрос
    requests_list.append({
        'insertText': {'location': {'index': 1}, 'text': all_text}
    })

    batch_url = f"{base_url}:batchUpdate"
    requests.post(batch_url, headers=headers_auth, json={'requests': requests_list})
    print("Документ обновлен и скрипт завершен.")

if __name__ == "__main__":
    clear_and_update()
