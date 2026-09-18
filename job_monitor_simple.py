#!/usr/bin/env python3
"""
Мониторинг вакансий в Telegram с выделением TOP вакансий
Требует: pip install requests APScheduler
"""

import requests
import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Tuple

# === КОНФИГ ===
TELEGRAM_BOT_TOKEN = "8888122150:AAEbM54G94Je0gTD5oy6Z6X3EQce7CYnCsI"
TELEGRAM_USER_ID = 574872
SALARY_MIN = 150000

# Ключевые слова для фильтрации
SEARCH_KEYWORDS = {
    'it_pm': ['pm', 'product manager', 'руководитель проекта', 'project manager', 'technical lead'],
    'communications': ['коммуникации', 'communications', 'внутренние коммуникации', 'internal communications'],
    'pr': ['pr', 'пиар', 'пресс', 'press', 'media relations', 'отношения со СМИ'],
    'admin': ['администратор', 'administrator', 'admin', 'coordination', 'координатор']
}

EXCLUDE_KEYWORDS = ['продажи', 'sales', 'агентство', 'agency', 'маркетинг агентство', 'digital agency']
GOOD_LOCATIONS = ['центр', 'невский', 'адмиралтейский', 'василеостровский', 'васильевский', 'петроградка', 'петроград']

# TOP вакансии — компании культуры, медиа, гуманитарные сферы
TOP_TIER_COMPANIES = ['театр', 'музей', 'издатель', 'publisher', 'media', 'медиа', 'культур', 'благотворит', 'charity', 'нго', 'образ', 'education', 'гуманитар', 'sevkabel', 'севкабель', 'богослов']

# VERY GOOD — крупные IT-продукты
VERY_GOOD_COMPANIES = ['яндекс', 'yandex', 'jetbrains', 'avito', 'озон', 'ozon', 'сбер', 'sber', 'mailru', 'mail.ru', 'лаборатория касперского', 'kaspersky', 'тинькофф', 'tinkoff']

# === ФУНКЦИИ ===

def is_good_location(location_text: str) -> bool:
    """Проверяет, находится ли вакансия в нужном месте"""
    location_lower = location_text.lower()
    
    if not any(x in location_lower for x in ['санкт-петербург', 'спб', 'петербург']):
        return False
    
    for area in GOOD_LOCATIONS:
        if area in location_lower:
            return True
    
    if ('центр' in location_lower or 'гибрид' in location_lower) and \
       not any(bad in location_lower for bad in ['пулково', 'невское', 'колпино']):
        return True
    
    return False

def matches_keywords(text: str) -> bool:
    """Проверяет, соответствует ли текст ключевым словам"""
    text_lower = text.lower()
    for keywords in SEARCH_KEYWORDS.values():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
    return False

def is_excluded(text: str) -> bool:
    """Проверяет исключающие слова"""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in EXCLUDE_KEYWORDS)

def parse_salary(salary_str: str) -> int:
    """Извлекает число из строки зарплаты"""
    if not salary_str:
        return 0
    
    import re
    numbers = re.findall(r'\d+', salary_str.replace(',', ''))
    if numbers:
        salary = int(numbers[0])
        if salary < 1000:
            salary *= 1000
        return salary
    return 0

def get_vacancy_hash(title: str, company: str, url: str) -> str:
    """Создаёт уникальный хеш вакансии"""
    content = f"{title}_{company}_{url}"
    return hashlib.md5(content.encode()).hexdigest()

def rate_vacancy(vacancy: Dict) -> Tuple[int, str]:
    """
    Ранжирует вакансию по привлекательности.
    Возвращает (рейтинг, пометка) где рейтинг: 3=TOP, 2=VERY GOOD, 1=GOOD
    """
    title = vacancy['title'].lower()
    company = vacancy['company'].lower()
    text = f"{title} {company}"
    
    # TOP tier — культура, медиа, гуманитарные сферы
    for keyword in TOP_TIER_COMPANIES:
        if keyword in text:
            return (3, "⭐⭐⭐ ИДЕАЛЬНО ПОДХОДИТ! (Культура/медиа/благотворительность)")
    
    # VERY GOOD tier — крупные IT-продукты
    for keyword in VERY_GOOD_COMPANIES:
        if keyword in text:
            return (2, "⭐⭐ ОЧЕНЬ ПОДХОДИТ! (Крупный IT-продукт)")
    
    # Остальное
    return (1, "⭐ Подходит")

def load_seen() -> set:
    """Загружает список уже отправленных вакансий"""
    if os.path.exists('seen.json'):
        with open('seen.json', 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_seen(hashes: set):
    """Сохраняет список отправленных вакансий"""
    with open('seen.json', 'w', encoding='utf-8') as f:
        json.dump(list(hashes), f)

def send_telegram(text: str, parse_mode: str = "HTML"):
    """Отправляет сообщение в Telegram"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_USER_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
        return False

def fetch_hh_vacancies() -> List[Dict]:
    """Собирает вакансии с HH.ru"""
    vacancies = []
    try:
        params = {
            'text': 'петербург',
            'area': 2,
            'per_page': 100,
            'page': 0,
            'schedule': 'fulltime,remote,flex'
        }
        
        response = requests.get('https://api.hh.ru/vacancies', params=params, timeout=10)
        response.encoding = 'utf-8'
        data = response.json()
        
        for item in data.get('items', []):
            title = item.get('name', '')
            company = item.get('employer', {}).get('name', '')
            url = item.get('alternate_url', '')
            location = item.get('area', {}).get('name', '')
            
            # Фильтруем
            if is_excluded(title + " " + company):
                continue
            if not is_good_location(location):
                continue
            if not matches_keywords(title):
                continue
            
            salary = item.get('salary')
            if salary:
                salary_from = salary.get('from')
                salary_to = salary.get('to')
                if salary_from and salary_from >= SALARY_MIN:
                    salary_str = f"от {salary_from:,} ₽"
                elif salary_to and salary_to >= SALARY_MIN:
                    salary_str = f"до {salary_to:,} ₽"
                else:
                    continue
            else:
                continue
            
            vacancies.append({
                'title': title,
                'company': company,
                'salary': salary_str,
                'url': url,
                'location': location,
                'platform': 'HH.ru'
            })
    
    except Exception as e:
        print(f"HH.ru ошибка: {e}")
    
    return vacancies

def format_message(vacancies: List[Dict]) -> str:
    """Форматирует список вакансий для Telegram с выделением TOP"""
    if not vacancies:
        return "Нет новых вакансий 😔"
    
    # Ранжируем вакансии
    rated = []
    for v in vacancies:
        rating, label = rate_vacancy(v)
        rated.append((rating, label, v))
    
    # Сортируем по рейтингу (TOP вперёд)
    rated.sort(key=lambda x: x[0], reverse=True)
    
    message = f"<b>🔍 Новые вакансии на {datetime.now().strftime('%d.%m %H:%M')}</b>\n\n"
    
    for rating, label, v in rated[:10]:
        message += f"""{label}
<b>{v['title']}</b>
<i>{v['company']}</i>
📍 {v['location']} | 💰 {v['salary']}
🔗 <a href="{v['url']}">Открыть</a>

"""
    
    return message.strip()

def run_monitor():
    """Основная функция мониторинга"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Поиск вакансий...")
    
    # Собираем вакансии
    all_vacancies = fetch_hh_vacancies()
    print(f"Найдено всего: {len(all_vacancies)} вакансий")
    
    # Фильтруем новые
    seen = load_seen()
    new_vacancies = []
    
    for v in all_vacancies:
        vac_hash = get_vacancy_hash(v['title'], v['company'], v['url'])
        if vac_hash not in seen:
            new_vacancies.append(v)
            seen.add(vac_hash)
    
    save_seen(seen)
    
    # Отправляем в Telegram
    if new_vacancies:
        print(f"✅ {len(new_vacancies)} новых вакансий")
        message = format_message(new_vacancies)
        send_telegram(message)
    else:
        print("Новых нет")

if __name__ == "__main__":
    run_monitor()
