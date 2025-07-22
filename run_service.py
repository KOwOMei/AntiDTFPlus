with open("find_me_in_system.txt", "w") as f:
    f.write("This file is created to ensure the script runs correctly.")
    
import sys
import os
import asyncio

# --- НАЧАЛО: КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ РАБОЧЕЙ ДИРЕКТОРИИ ---
# Этот блок должен быть самым первым.
if getattr(sys, 'frozen', False):
    # Если приложение "заморожено", меняем рабочую директорию
    # на ту, где лежит сам .exe файл.
    try:
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
    except Exception as e:
        # Если не удалось сменить директорию, это критично.
        # Можно добавить запись в лог, если необходимо.
        print(f"Fatal: Could not change directory. Error: {e}")
        sys.exit(1)
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---

# Этот блок исправляет пути импорта, когда приложение "заморожено" PyInstaller.
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    sys.path.append(base_path)

# Теперь импортируем только то, что нужно для запуска
from src.auto_service import main_async

# --- НОВЫЙ БЛОК ЗАПУСКА ---
# Этот код будет выполняться, когда Task Scheduler запустит .exe
if __name__ == '__main__':
    try:
        # Просто запускаем основную асинхронную функцию
        asyncio.run(main_async())
    except KeyboardInterrupt:
        # Это полезно для отладки из командной строки
        print("Процесс прерван пользователем.")
    except Exception as e:
        # Логирование критической ошибки
        # (Логгер настраивается внутри auto_service.py)
        print(f"Фатальная ошибка в приложении: {e}")