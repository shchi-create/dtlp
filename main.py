import os
import json
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Читаем переменные
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
DOCUMENT_ID = os.getenv("DOCUMENT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

def get_service():
    # Проверка: если переменная пустая, выводим понятную ошибку
    if not GOOGLE_CREDS_JSON:
        raise ValueError("ОШИБКА: Переменная GOOGLE_APPLICATION_CREDENTIALS_JSON не установлена!")
    
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/documents'])
    return build('docs', 'v1', credentials=creds)

def clear_and_update():
    if not CHANNEL_NAME or not DOCUMENT_ID:
        print("ОШИБКА: Не заполнены CHANNEL_NAME или DOCUMENT_ID")
        return

    service = get_service()
    
    # 1. Получаем размер документа
    doc = service.documents().get(documentId=DOCUMENT_ID).execute()
    content = doc.get('body').get('content')
    end_index = content[-1].get('endIndex')
    
    requests_list = []
    
    # Удаляем всё, если в документе есть что-то кроме пустой строки
    if end_index > 2:
        requests_list.append({
            'deleteContentRange': {
                'range': {'startIndex': 1, 'endIndex': end_index - 1}
            }
        })

    # 2. Парсим Telegram
    print(f"Загружаю сообщения из t.me/s/{CHANNEL_NAME}...")
    url = f"https://t.me/s/{CHANNEL_NAME}"
    # Добавили headers, чтобы Telegram не принял нас за бота-агрессора
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Собираем тексты
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    
    # Инвертируем список, если нужно, чтобы новые были внизу, 
    # или оставляем так, чтобы новые были сверху
    all_text = ""
    for msg in messages:
        text = msg.get_text(separator='\n').strip()
        all_text += f"{text}\n{'-'*20}\n\n"

    if not all_text:
        all_text = "Текстовых сообщений не обнаружено."

    # 3. Вставляем текст
    requests_list.append({
        'insertText': {
            'location': {'index': 1},
            'text': all_text
        }
    })

    service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests_list}).execute()
    print("Готово! Документ обновлен.")

if __name__ == "__main__":
    try:
        clear_and_update()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
