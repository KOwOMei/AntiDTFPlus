import tkinter as tk
from tkinter import ttk, messagebox
import threading
import asyncio
from ..dtf_api import get_subsite_posts, find_and_delete_plus_users_comments

class PostSelectionMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.posts = [] # Будем хранить здесь полный список постов

        label = tk.Label(self, text="Выбор поста для очистки", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # Фрейм для списка и скроллбара
        list_frame = tk.Frame(self)
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.posts_listbox = tk.Listbox(list_frame)
        self.posts_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.posts_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.posts_listbox.config(yscrollcommand=scrollbar.set)

        # Фрейм для кнопок
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10, padx=20, fill="x")

        button_delete = ttk.Button(button_frame, text="Удалить Plus-комментарии в выбранном посте",
                                   command=self.confirm_delete_for_selected)
        button_delete.pack(side="left", expand=True, padx=5)

        button_back = ttk.Button(button_frame, text="Назад в меню",
                                 command=lambda: controller.show_frame("MainMenu"))
        button_back.pack(side="right", expand=True, padx=5)

        # Привязываем событие показа окна к загрузке постов
        self.bind("<<ShowFrame>>", self.on_show_frame)

    def on_show_frame(self, event):
        """Событие, которое вызывается, когда окно становится видимым."""
        self.load_posts()

    def load_posts(self):
        """Запускает асинхронную загрузку постов в отдельном потоке."""
        self.posts_listbox.delete(0, tk.END)
        self.posts_listbox.insert(tk.END, "Загрузка постов...")
        threading.Thread(target=self._async_load_posts, daemon=True).start()

    def _async_load_posts(self):
        """Асинхронная функция для получения и отображения постов."""
        async def task():
            if not self.controller.user_id:
                messagebox.showerror("Ошибка", "ID пользователя не найден. Невозможно загрузить посты.")
                self.posts_listbox.delete(0, tk.END)
                self.posts_listbox.insert(tk.END, "Ошибка: ID пользователя не найден.")
                return

            self.posts = await get_subsite_posts(self.controller.user_id, self.controller.token_manager)
            
            self.posts_listbox.delete(0, tk.END) # Очищаем список
            if not self.posts:
                self.posts_listbox.insert(tk.END, "Посты не найдены.")
            else:
                for post in self.posts:
                    # Убедимся, что у поста есть поле 'data'
                    title = post.get('data', {}).get('title', 'Пост без заголовка')
                    self.posts_listbox.insert(tk.END, title)
        
        asyncio.run(task())

    def confirm_delete_for_selected(self):
        """Подтверждает и запускает удаление комментариев для выбранного поста."""
        selected_indices = self.posts_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Внимание", "Пожалуйста, выберите пост из списка.")
            return
        
        selected_index = selected_indices[0]
        selected_post = self.posts[selected_index]
        post_id = selected_post.get('id')
        post_title = selected_post.get('title', 'Пост без заголовка')

        if not post_id:
            messagebox.showerror("Ошибка", "Не удалось получить ID для выбранного поста.")
            return

        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить все комментарии от пользователей с DTF Plus под постом «{post_title}»?"):
            threading.Thread(target=self._async_delete_comments, args=(post_id,), daemon=True).start()

    def _async_delete_comments(self, post_id):
        """Асинхронная функция для удаления комментариев."""
        async def task():
            messagebox.showinfo("В процессе", "Начинаю удаление комментариев. Это может занять некоторое время...")
            deleted_count = await find_and_delete_plus_users_comments('one_post', post_id, self.controller.user_id, self.controller.token_manager)
            messagebox.showinfo("Успех", f"Удалено {deleted_count} комментариев.")

        asyncio.run(task())