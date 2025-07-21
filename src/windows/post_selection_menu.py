import tkinter as tk
from tkinter import ttk

class PostSelectionMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        label = tk.Label(self, text="Выбор поста", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # Здесь может быть список постов
        posts_listbox = tk.Listbox(self)
        for i in range(1, 21):
            posts_listbox.insert(tk.END, f"Пост номер {i}")
        posts_listbox.pack(pady=10, padx=20, fill="both", expand=True)


        button_back = ttk.Button(self, text="Назад в меню",
                                 command=lambda: controller.show_frame("MainMenu"))
        button_back.pack(pady=10)