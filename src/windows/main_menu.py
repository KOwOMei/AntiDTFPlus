import tkinter as tk
from tkinter import ttk, messagebox
import win32service
import win32serviceutil
import ctypes
import os
import sys 
from ..dtf_api import find_and_delete_plus_users_comments

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Создаем Label, но пока с пустым текстом
        self.welcome_label = tk.Label(self, text="Привет, Анон!", font=controller.title_font)
        self.welcome_label.pack(side="top", fill="x", pady=10)

        button_select_post = ttk.Button(self, text="Выбрать пост",
                                        command=lambda: controller.show_frame("PostSelectionMenu"))
        button_select_post.pack(pady=10)

        button_all_posts = ttk.Button(self, text="Удалить Plus-комментарии под всеми постами",
                                       command=self.are_you_sure)
        button_all_posts.pack(pady=10)

        button_install_service = ttk.Button(self, text="Установить службу автозапуска",
                                            command=self.install_service)
        button_install_service.pack(pady=10)

        button_uninstall_service = ttk.Button(self, text="Удалить службу автозапуска",
                                             command=self.uninstall_service)
        button_uninstall_service.pack(pady=10)

        button_logout = ttk.Button(self, text="Выйти из аккаунта",
                                   command=lambda: controller.show_frame("AuthWindow"))
        button_logout.pack(pady=10)

        # Привязываем событие показа окна к обновлению текста
        self.bind("<<ShowFrame>>", self.on_show_frame)

    def on_show_frame(self, event):
        """Обновляет приветственную надпись, когда окно становится видимым."""
        user_name = self.controller.user_name or "Пользователь"
        self.welcome_label.config(text=f"Приветствую, {user_name}!")

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    async def are_you_sure(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить все комментарии от пользователей с подпиской DTF Plus ПОД ВСЕМИ ВАШИМИ ПОСТАМИ??? Это действие необратимо!"):
            plus_comments_deleted = await find_and_delete_plus_users_comments('all_posts', None, self.controller.user_id, self.controller.token_manager)
            messagebox.showinfo("Успех", f"Программа успешно удалила {plus_comments_deleted} комментариев под всеми вашими постами!")
        else:
            messagebox.showinfo("Отмена", "Удаление комментариев отменено.")

    def _run_as_admin(self):
        """Перезапускает приложение с правами администратора."""
        if self.is_admin():
            return True # Уже запущены с правами администратора

        if messagebox.askyesno("Требуются права администратора", 
                               "Для выполнения этого действия приложению требуются права администратора. "
                               "Перезапустить приложение с запросом на повышение прав?"):
            try:
                # Используем системный вызов для перезапуска с запросом прав
                ret_code = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                
                if ret_code > 32:
                    # Запрос на запуск был успешным, закрываем текущий процесс
                    sys.exit(0)
                    return False # Возвращаем False, т.к. текущий процесс завершается
                else:
                    # Если код <= 32, произошла ошибка при попытке запуска
                    messagebox.showerror("Ошибка", f"Не удалось запустить процесс с правами администратора. Код ошибки: {ret_code}")
                    return False

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось перезапустить приложение с правами администратора:\n{e}")
                return False
        else:
            return False # Пользователь отказался

    def install_service(self):
        if not self._run_as_admin():
            return

        if messagebox.askyesno("Подтверждение", "Вы действительно хотите установить службу, которая будет запускаться вместе с Windows?"):
            try:
                # Шаг 1: Принудительная очистка старой службы (если она есть)
                try:
                    win32serviceutil.StopService('AntiDTFPlusService')
                    win32serviceutil.RemoveService('AntiDTFPlusService')
                    messagebox.showinfo("Очистка", "Обнаружена и удалена предыдущая версия службы.")
                except Exception as e:
                    if "The specified service does not exist" not in str(e):
                        print(f"Предупреждение при очистке: {e}")

                # Шаг 2: Установка новой службы
                service_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "auto_service.py"))
                
                if not os.path.exists(service_file):
                    messagebox.showerror("Ошибка", f"Файл службы не найден: {service_file}")
                    return

                # Путь к обработчику службы, который лежит рядом с основным EXE
                service_handler_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "AntiDTFPlusServiceHandler.exe"))

                if not os.path.exists(service_handler_path):
                    messagebox.showerror("Ошибка", f"Файл обработчика службы не найден: {service_handler_path}")
                    return

                win32serviceutil.InstallService(
                    service_handler_path, # Указываем путь к нашему второму EXE
                    'AntiDTFPlusService',
                    'AntiDTFPlus Auto-Start Service',
                    startType=win32service.SERVICE_AUTO_START
                )
                win32serviceutil.StartService('AntiDTFPlusService')
                messagebox.showinfo("Успех", "Служба успешно установлена и запущена.")
            except Exception as e:
                messagebox.showerror("Ошибка установки", f"Не удалось установить службу:\n{e}")
    
    def uninstall_service(self):
        if not self._run_as_admin():
            return # Прерываем выполнение, если права не были получены

        if messagebox.askyesno("Подтверждение", "Вы действительно хотите удалить службу?"):
            try:
                win32serviceutil.StopService('AntiDTFPlusService')
                win32serviceutil.RemoveService('AntiDTFPlusService')
                messagebox.showinfo("Успех", "Служба успешно остановлена и удалена.")
            except Exception as e:
                # Игнорируем ошибку, если служба уже была удалена или не установлена
                if "The specified service does not exist" in str(e):
                     messagebox.showinfo("Информация", "Служба не была установлена.")
                else:
                    messagebox.showerror("Ошибка удаления", f"Не удалось удалить службу:\n{e}")
