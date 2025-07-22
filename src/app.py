import tkinter as tk
from tkinter import font as tkfont
import asyncio

from .windows.auth_window import AuthWindow
from .windows.main_menu import MainMenu
from .windows.post_selection_menu import PostSelectionMenu
from .dtf_api import TokenManager, get_user_info

class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.title("AntiDTFPlus")
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold")
        
        self.token_manager = TokenManager()
        self.user_id = None
        self.user_name = None

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (AuthWindow, MainMenu, PostSelectionMenu):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Запускаем асинхронную проверку входа
        asyncio.run(self.try_auto_login())

    async def try_auto_login(self):
        """Пытается войти, используя сохраненные токены."""
        if self.token_manager.refresh_token:
            # Если есть refresh_token, пытаемся обновить токен доступа
            await self.token_manager.refresh()
        
        if self.token_manager.access_token:
            # Если токен доступа есть (после обновления или он был валиден), получаем данные пользователя
            user_data = await get_user_info(self.token_manager)
            if user_data and 'id' in user_data:
                self.user_id = user_data['id']
                self.user_name = user_data.get('name', 'Неизвестный пользователь')
                print(f"Автоматический вход успешен. User ID: {self.user_id}")
                self.show_frame("MainMenu")
                return

        # Если автоматический вход не удался, показываем окно аутентификации
        print("Автоматический вход не удался. Показываю окно входа.")
        self.show_frame("AuthWindow")


    def show_frame(self, page_name):
        '''Показать окно по его имени'''
        frame = self.frames[page_name]
        # Генерируем событие, чтобы окно знало, что его сейчас покажут
        frame.event_generate("<<ShowFrame>>") 
        frame.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()