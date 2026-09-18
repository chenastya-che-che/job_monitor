#!/usr/bin/env python3
"""
Планировщик запусков мониторинга 3 раза в день
Требует: pip install APScheduler
"""

from apscheduler.schedulers.background import BackgroundScheduler
from job_monitor_simple import run_monitor
from datetime import datetime
import time
import sys

def main():
    print("=" * 60)
    print("🚀 Мониторинг вакансий запущен")
    print("=" * 60)
    print(f"⏰ Время сервера: {datetime.now()}")
    print("📅 Запуски в: 08:00, 14:00, 20:00")
    print("🔔 Проверь что Telegram бот открыт (@anastya_job_seeker_bot)")
    print("⛔ Для остановки нажми Ctrl+C\n")
    
    scheduler = BackgroundScheduler()
    
    # Добавляем расписание
    scheduler.add_job(run_monitor, 'cron', hour=8, minute=0, id='morning')
    scheduler.add_job(run_monitor, 'cron', hour=14, minute=0, id='afternoon')
    scheduler.add_job(run_monitor, 'cron', hour=20, minute=0, id='evening')
    
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⛔ Планировщик остановлен")
        scheduler.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()
