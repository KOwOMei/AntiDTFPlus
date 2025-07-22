import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from ..dtf_api import TokenManager, get_user_info

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

        login_pass_button = ttk.Button(login_frame, text="Войти по логину и паролю",
                                       command=self.login_with_password)
        login_pass_button.pack(pady=10, padx=10)

        # Фрейм для входа по refreshToken
        token_frame = ttk.LabelFrame(self, text="Вход по токену")
        token_frame.pack(pady=10, padx=20, fill="x")

        ttk.Label(token_frame, text="refreshToken:").pack(padx=10, pady=5, anchor="w")
        self.refresh_token_entry = ttk.Entry(token_frame, show="*")
        self.refresh_token_entry.pack(padx=10, pady=5, fill="x")
        
        refresh_token_button = ttk.Button(token_frame, text="Войти по токену",
                                          command=self.login_with_refresh_token)
        refresh_token_button.pack(pady=10, padx=10)

    def login_with_password(self):
        email = self.email_entry.get()
        password = self.password_entry.get()
        if not email or not password:
            messagebox.showerror("Ошибка", "Email и пароль не могут быть пустыми.")
            return

        # Запускаем асинхронную функцию в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(target=self._async_login, args=(email, password), daemon=True).start()

    def login_with_refresh_token(self):
        token = self.refresh_token_entry.get()
        if not token:
            messagebox.showerror("Ошибка", "refreshToken не может быть пустым.")
            return
        # Запускаем асинхронную функцию в отдельном потоке
        threading.Thread(target=self._async_refresh, args=(token,), daemon=True).start()

    def _async_login(self, email, password):
        async def task():
            # Используем token_manager из controller'а
            self.controller.token_manager.email = email
            self.controller.token_manager.password = password
            success = await self.controller.token_manager.login()
            if success:
                # После успешного входа получаем user_id
                user_data = await get_user_info(self.controller.token_manager)
                if user_data and 'id' in user_data:
                    self.controller.user_id = user_data['id']
                    self.controller.show_frame("MainMenu")
                else:
                    messagebox.showerror("Ошибка", "Не удалось получить информацию о пользователе после входа.")
            else:
                messagebox.showerror("Ошибка входа", "Не удалось войти. Проверьте email, пароль и консоль на наличие ошибок.")
        
        asyncio.run(task())

    def _async_refresh(self, token):
        async def task():
            # Используем token_manager из controller'а и устанавливаем токен из поля ввода
            self.controller.token_manager.refresh_token = token
            await self.controller.token_manager.refresh()
            
            if self.controller.token_manager.access_token:
                # После успешного обновления получаем user_id
                user_data = await get_user_info(self.controller.token_manager)
                if user_data and 'id' in user_data:
                    self.controller.user_id = user_data['id']
                    # Сохраняем токен в кэш для будущих авто-входов
                    self.controller.token_manager._save_tokens_to_cache()
                    self.controller.show_frame("MainMenu")
                else:
                    messagebox.showerror("Ошибка", "Не удалось получить информацию о пользователе после обновления токена.")
            else:
                messagebox.showerror("Ошибка входа", "Не удалось войти по refreshToken. Токен недействителен или истек.")

        asyncio.run(task())