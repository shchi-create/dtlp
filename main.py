import requests
import re
import os
import json
import logging
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# --- ЛОГИ ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# --- ENV ---
CHANNEL_NAME = os.getenv("CHANNEL_NAME")
DOCUMENT_ID = os.getenv("DOCUMENT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")


# ---------------------------------------------------
# GOOGLE DOCS
# ---------------------------------------------------

def get_google_docs_service():
    scopes = ['https://www.googleapis.com/auth/documents']

    if not GOOGLE_CREDS_JSON:
        raise ValueError("GOOGLE creds missing")

    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=scopes
    )

    return build('docs', 'v1', credentials=creds)


def get_doc_end_index(service):
    doc = service.documents().get(documentId=DOCUMENT_ID).execute()
    content = doc.get('body').get('content', [])
    return content[-1]['endIndex']


def clear_document(service):
    """
    Полностью очищает документ
    """
    end_index = get_doc_end_index(service)

    # если документ пуст — нечего чистить
    if end_index <= 2:
        return

    requests_body = [{
        'deleteContentRange': {
            'range': {
                'startIndex': 1,
                'endIndex': end_index - 1
            }
        }
    }]

    service.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={'requests': requests_body}
    ).execute()

    logging.info("Документ очищен")


def write_document(service, text):
    requests_body = [{
        'insertText': {
            'location': {'index': 1},
            'text': text
        }
    }]

    service.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={'requests': requests_body}
    ).execute()


# ---------------------------------------------------
# ПАРСИНГ
# ---------------------------------------------------

def parse_to_google_doc():

    logging.info("Старт")

    service = get_google_docs_service()

    url = f"https://t.me/s/{CHANNEL_NAME}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    messages = soup.find_all('div', class_='tgme_widget_message_wrap')

    today = datetime.now().strftime("%d.%m.%Y")

    headline_pattern = re.compile(
        r"Актуальный новостной фон на\s*(\d{2}\.\d{2}\.\d{4})"
    )

    target_entry = None

    for msg in messages:

        text_area = msg.find('div', class_='tgme_widget_message_text')
        if not text_area:
            continue

        text = text_area.get_text(separator="\n").strip()
        first_line = text.splitlines()[0]

        match = headline_pattern.search(first_line)
        if not match:
            continue

        post_date = match.group(1)

        if post_date != today:
            logging.info(f"Дата {post_date} не сегодняшняя")
            continue

        link_tag = msg.find('a', class_='tgme_widget_message_date')
        link = link_tag['href'] if link_tag else "[нет ссылки]"

        target_entry = f"{link}\n{text}\n"
        break

    # --- запись ---
    if target_entry:

        final_text = f"--- ЗАГРУЗКА ОТ {today} ---\n\n{target_entry}"

        clear_document(service)
        write_document(service, final_text)

        logging.info("Пост записан")

    else:
        logging.info("Пост за сегодня не найден")


# ---------------------------------------------------

if __name__ == "__main__":
    parse_to_google_doc()
