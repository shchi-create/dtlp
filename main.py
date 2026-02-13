import os
import json
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Настройки из переменных окружения
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
DOCUMENT_ID = os.getenv("DOCUMENT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

def get_service():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/documents'])
    return build('docs', 'v1', credentials=creds)

def clear_and_update():
    service = get_service()
    
    # 1. Получаем текущий размер документа, чтобы знать, что удалять
    doc = service.documents().get(documentId=DOCUMENT_ID).execute()
    end_index = doc.get('body').get('content')[-1].get('endIndex')
    
    # Подготавливаем список команд (requests)
    requests_list = []
    
    # Удаляем всё содержимое, если оно есть (индекс 1 — начало, end_index-1 — конец)
    if end_index > 2:
        requests_list.append({
            'deleteContentRange': {
                'range': {'startIndex': 1, 'endIndex': end_index - 1}
            }
        })

    # 2. Парсим Telegram (публичную версию канала)
    url = f"https://t.me/s/{CHANNEL_NAME}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Собираем все текстовые сообщения
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    all_text = ""
    for msg in messages:
        all_text += msg.get_text(separator='\n').strip() + "\n" + ("-"*30) + "\n\n"

    if not all_text:
        all_text = "Сообщений не найдено или канал пуст."

    # 3. Вставляем новый текст
    requests_list.append({
        'insertText': {
            'location': {'index': 1},
            'text': all_text
        }
    })

    # Выполняем всё одним запросом
    service.documents().batchUpdate(
        documentId=DOCUMENT_ID, 
        body={'requests': requests_list}
    ).execute()
    print("Документ успешно обновлен!")

if __name__ == "__main__":
    clear_and_update()
