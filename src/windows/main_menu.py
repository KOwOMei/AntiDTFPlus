import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import ctypes
import win32serviceutil
from ..dtf_api import TokenManager, find_and_delete_plus_users_comments

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        label = tk.Label(self, text="Основное меню", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        button_select_post = ttk.Button(self, text="Выбрать пост",
                                        command=lambda: controller.show_frame("PostSelectionMenu"))
        button_select_post.pack(pady=10)

        button_select_post = ttk.Button(self, text="Удалить комментарии под всеми постами",
                                        command=lambda: find_and_delete_plus_users_comments(controller.token_manager))
        button_select_post.pack(pady=10)

        button_install_service = ttk.Button(self, text="Установить службу автозапуска",
                                            command=self.install_service)
        button_install_service.pack(pady=10)

        button_logout = ttk.Button(self, text="Выйти",
                                   command=lambda: controller.show_frame("AuthWindow"))
        button_logout.pack()

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def install_service(self):
        if not self.is_admin():
            messagebox.showerror("Ошибка", "Для установки службы требуются права администратора. Перезапустите приложение от имени администратора.")
            return

        if messagebox.askyesno("Подтверждение", "Вы действительно хотите установить службу, которая будет запускаться вместе с Windows?"):
            try:
                # Путь к вашему интерпретатору Python и скрипту службы
                # Важно: Создайте файл 'my_service.py' из следующего шага
                service_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "my_service.py"))
                
                # Проверяем, существует ли файл службы
                if not os.path.exists(service_file):
                    messagebox.showerror("Ошибка", f"Файл службы не найден: {service_file}")
                    return

                # Установка службы
                win32serviceutil.InstallService(
                    pythonClassString=f"{os.path.splitext(os.path.basename(service_file))[0]}.MyService",
                    serviceName='AntiDTFPlusService',
                    displayName='AntiDTFPlus Auto-Start Service',
                    startType='auto' # Автоматический запуск
                )
                messagebox.showinfo("Успех", "Служба успешно установлена и будет запускаться автоматически.")
            except Exception as e:
                messagebox.showerror("Ошибка установки", f"Не удалось установить службу:\n{e}")