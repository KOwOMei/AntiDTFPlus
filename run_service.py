import sys
import os
import win32serviceutil

# Этот блок исправляет пути импорта, когда приложение "заморожено" PyInstaller.
# Он должен быть в самом верху.
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