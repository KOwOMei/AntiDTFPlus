import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from ..dtf_api import TokenManager

class AuthWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        label = tk.Label(self, text="Окно аутентификации", font=controller.title_font)
        label.pack(side="top", fill="x", pady=20)

        # Фрейм для входа по логину и паролю
        login_frame = ttk.LabelFrame(self, text="Вход по логину и паролю")
        login_frame.pack(pady=10, padx=20, fill="x")

        ttk.Label(login_frame, text="Email:").pack(padx=10, pady=5, anchor="w")
        self.email_entry = ttk.Entry(login_frame)
        self.email_entry.pack(padx=10, pady=5, fill="x")

        ttk.Label(login_frame, text="Пароль:").pack(padx=10, pady=5, anchor="w")
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.pack(padx=10, pady=5, fill="x")

        login_pass_button = ttk.Button(login_frame, text="Войти",
                                       command=self.login_with_password)
        login_pass_button.pack(pady=10, padx=10)

        # Кнопка для входа по refreshToken
        refresh_token_button = ttk.Button(self, text="Вход по сохраненному токену (refreshToken)",
                                          command=self.login_with_refresh_token)
        refresh_token_button.pack(pady=20, padx=20, fill='x')

    def login_with_password(self):
        email = self.email_entry.get()
        password = self.password_entry.get()
        if not email or not password:
            messagebox.showerror("Ошибка", "Email и пароль не могут быть пустыми.")
            return

        # Запускаем асинхронную функцию в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(target=self._async_login, args=(email, password), daemon=True).start()

    def login_with_refresh_token(self):
        # Запускаем асинхронную функцию в отдельном потоке
        threading.Thread(target=self._async_refresh, daemon=True).start()

    def _async_login(self, email, password):
        async def task():
            # Используем token_manager из controller'а
            self.controller.token_manager.email = email
            self.controller.token_manager.password = password
            success = await self.controller.token_manager.login()
            if success:
                self.controller.show_frame("MainMenu")
            else:
                messagebox.showerror("Ошибка входа", "Не удалось войти. Проверьте email, пароль и консоль на наличие ошибок.")
        
        asyncio.run(task())

    def _async_refresh(self):
        async def task():
            # Убедимся, что токены загружены из кэша
            self.controller.token_manager._load_tokens_from_cache()
            if not self.controller.token_manager.refresh_token:
                messagebox.showerror("Ошибка", "Сохраненный refreshToken не найден.")
                return

            await self.controller.token_manager.refresh()
            
            if self.controller.token_manager.access_token:
                self.controller.show_frame("MainMenu")
            else:
                messagebox.showerror("Ошибка входа", "Не удалось войти по refreshToken. Попробуйте войти по логину и паролю.")

        asyncio.run(task())