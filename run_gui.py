import ctypes
import sys
import os
from src.app import App

def is_admin():
    """Проверяет, запущено ли приложение с правами администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# --- НАЧАЛО: ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ПРИ ЗАПУСКЕ ---
if not is_admin():
    # Если права отсутствуют, перезапускаем этот же скрипт с запросом повышения прав.
    try:
        # 'runas' - это команда для запроса повышения прав (UAC).
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    except Exception as e:
        # На случай, если пользователь откажется или произойдет ошибка.
        print(f"Не удалось перезапустить приложение с правами администратора: {e}")
    
    # Закрываем текущий процесс без прав, чтобы не было двух окон.
    sys.exit(0)
# --- КОНЕЦ ПРОВЕРКИ ---

if __name__ == "__main__":
    app = App()
    app.mainloop()