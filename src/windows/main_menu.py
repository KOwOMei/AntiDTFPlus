import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys 
import subprocess
import ctypes  # <-- Добавьте этот импорт
from ..dtf_api import find_and_delete_plus_users_comments

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Создаем Label, но пока с пустым текстом
        self.welcome_label = tk.Label(self, text="Привет, Анон!", font=controller.title_font)
        self.welcome_label.pack(side="top", fill="x", pady=10)

        button_select_post = ttk.Button(self, text="Удалить комментарии от Plus-подписчиков в определенном посте",
                                        command=lambda: controller.show_frame("PostSelectionMenu"))
        button_select_post.pack(pady=10)

        button_all_posts = ttk.Button(self, text="Удалить комментарии от Plus-подписчиков под всеми постами",
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

        self.bind("<<ShowFrame>>", self.on_show_frame)

    def on_show_frame(self, event):
        """Обновляет приветственную надпись, когда окно становится видимым."""
        user_name = self.controller.user_name or "Пользователь"
        self.welcome_label.config(text=f"Приветствую, {user_name}!")

    async def are_you_sure(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить все комментарии от пользователей с подпиской DTF Plus ПОД ВСЕМИ ВАШИМИ ПОСТАМИ??? Это действие необратимо!"):
            plus_comments_deleted = await find_and_delete_plus_users_comments('all_posts', None, self.controller.user_id, self.controller.token_manager)
            messagebox.showinfo("Успех", f"Программа успешно удалила {plus_comments_deleted} комментариев под всеми вашими постами!")
        else:
            messagebox.showinfo("Отмена", "Удаление комментариев отменено.")

    def is_admin(self):
        """Проверяет, запущено ли приложение с правами администратора."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def _run_as_admin(self):
        """
        Проверяет права администратора. Если их нет, предлагает перезапустить
        приложение с повышенными правами.
        Возвращает True, если права есть, и False, если нет.
        """
        if self.is_admin():
            return True
        
        if messagebox.askyesno(
            "Требуются права администратора",
            "Для этой операции требуются права администратора.\n\n"
            "Перезапустить приложение с запросом прав?"
        ):
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0) 
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось перезапустить приложение:\n{e}")
        return False

    def install_service(self):
        """Создает задачу в Планировщике заданий для автозапуска."""
        if not self._run_as_admin():
            return 

        if messagebox.askyesno("Подтверждение", "Вы хотите, чтобы программа автоматически запускалась в фоновом режиме при каждом входе в Windows?"):
            try:
                task_name = "AntiDTFPlusAutostart"
                # Важно: мы запускаем тот же .exe, что и для службы, т.к. в нем нет GUI
                program_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "AntiDTFPlusServiceHandler.exe"))

                if not os.path.exists(program_path):
                    messagebox.showerror("Ошибка", f"Не найден файл для автозапуска:\n{program_path}")
                    return

                # Команда для создания задачи в Планировщике
                # /SC ONLOGON - запускать при входе пользователя
                # /RL HIGHEST - с максимальными доступными правами
                # /F - перезаписать, если задача уже существует
                command = [
                    'schtasks', '/create', '/tn', task_name, '/tr', f'"{program_path}"',
                    '/sc', 'ONLOGON', '/rl', 'HIGHEST', '/f'
                ]
                
                # Запускаем команду без создания окна консоли
                subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Запускаем службу сразу же, не дожидаясь перезагрузки
                subprocess.Popen([program_path], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
                
                messagebox.showinfo("Успех", "Программа успешно добавлена в автозапуск.\nОна будет стартовать автоматически при следующем входе в систему.")

            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('cp866', errors='ignore')
                messagebox.showerror("Ошибка", f"Не удалось создать задачу в автозапуске:\n{error_message}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Произошла непредвиденная ошибка:\n{e}")

    def uninstall_service(self):
        """Удаляет задачу из Планировщика заданий."""
        if not self._run_as_admin():
            return

        if messagebox.askyesno("Подтверждение", "Вы действительно хотите убрать программу из автозапуска?"):
            try:
                task_name = "AntiDTFPlusAutostart"
                
                # Команда для удаления задачи
                command = ['schtasks', '/delete', '/tn', task_name, '/f']
                
                # Запускаем команду без создания окна консоли
                subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                messagebox.showinfo("Успех", "Программа успешно удалена из автозапуска.")

            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('cp866', errors='ignore')
                # Игнорируем ошибку, если задачи и так не было
                if "не найдена" in error_message.lower() or "not found" in error_message.lower():
                    messagebox.showinfo("Информация", "Программа и так не была в автозапуске.")
                else:
                    messagebox.showerror("Ошибка", f"Не удалось удалить задачу из автозапуска:\n{error_message}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Произошла непредвиденная ошибка:\n{e}")
