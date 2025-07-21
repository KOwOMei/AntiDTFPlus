import tkinter as tk
from tkinter import font as tkfont

from .windows.auth_window import AuthWindow
from .windows.main_menu import MainMenu
from .windows.post_selection_menu import PostSelectionMenu
from .dtf_api import TokenManager

class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("AntiDTFPlus")
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold")
        
        # Создаем экземпляр TokenManager
        self.token_manager = TokenManager(email=None, password=None)

        # Контейнер, где будут размещаться все окна (фреймы)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # Создание и сохранение всех окон
        for F in (AuthWindow, MainMenu, PostSelectionMenu):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Показать стартовое окно
        self.show_frame("AuthWindow")

    def show_frame(self, page_name):
        '''Показать окно по его имени'''
        frame = self.frames[page_name]
        frame.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()