with open("find_me_in_system.txt", "w") as f:
    f.write("This file is created to ensure the script runs correctly.")
    
import sys
import os

# --- НАЧАЛО: КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ РАБОЧЕЙ ДИРЕКТОРИИ ---
# Этот блок должен быть самым первым, до всех остальных импортов.
if getattr(sys, 'frozen', False):
    # Если приложение "заморожено" PyInstaller, то мы определяем путь к .exe
    application_path = os.path.dirname(sys.executable)
    # и меняем текущую рабочую директорию на директорию с .exe
    os.chdir(application_path)
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---

import win32serviceutil

# Этот блок исправляет пути импорта, когда приложение "заморожено" PyInstaller.
if getattr(sys, 'frozen', False):
    # sys._MEIPASS - это путь к временной папке, куда PyInstaller распаковывает все файлы
    base_path = sys._MEIPASS
    sys.path.append(base_path)

# Теперь, когда пути исправлены, можно импортировать класс службы
from src.auto_service import AntiDTFPlusService

if __name__ == '__main__':
    # Эта функция из pywin32 обрабатывает аргументы командной строки
    # (install, start, stop, debug и т.д.) и запускает службу.
    win32serviceutil.HandleCommandLine(AntiDTFPlusService)