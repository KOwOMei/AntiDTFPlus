import asyncio
import json
import os
import httpx
import logging
from typing import Literal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Настройка сохранения логов в файл
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_formatter)
logging.getLogger().addHandler(file_handler)

TOKEN_CACHE_FILE = "token_cache.json"

class TokenManager:
    def __init__(self, email: str | None = None, password: str | None = None):
        self.email = email
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self._load_tokens_from_cache()

    def _load_tokens_from_cache(self):
        """Загружает токены из файла кэша при инициализации."""
        try:
            if os.path.exists(TOKEN_CACHE_FILE):
                with open(TOKEN_CACHE_FILE, 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get("accessToken")
                    self.refresh_token = tokens.get("refreshToken")
                    if self.access_token and self.refresh_token:
                        logger.info("✅ TokenManager: Токены успешно загружены из кэша.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("⚠️ TokenManager: Не удалось загрузить токены из кэша: %s", e)

    def _save_tokens_to_cache(self):
        """Сохраняет текущие токены в файл кэша."""
        tokens = {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token
        }
        with open(TOKEN_CACHE_FILE, 'w') as f:
            json.dump(tokens, f)
        logger.info("💾 TokenManager: Токены сохранены в кэш.")

    async def login(self) -> bool:
        """Выполняет первоначальный вход и сохраняет токены."""
        if self.access_token and self.refresh_token:
            logger.info("✅ TokenManager: Токены уже есть, вход не требуется.")
            return True

        url = "https://api.dtf.ru/v3.4/auth/email/login"
        payload = {"email": self.email, "password": self.password}
        headers = {"User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                self.access_token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
                if self.access_token and self.refresh_token:
                    logger.info("✅ TokenManager: Успешный вход, токены получены.")
                    self._save_tokens_to_cache()
                    return True
        logger.error("❌ TokenManager: Ошибка входа.")
        return False

    async def refresh(self):
        """Обновляет токены, используя refresh_token."""
        if not self.refresh_token:
            logger.warning("⚠️ TokenManager: Нет refresh_token для обновления. Попытка полного входа.")
            await self.login()
            return

        url = "https://api.dtf.ru/v3.4/auth/refresh"
        payload = {"token": self.refresh_token}
        headers = {"User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                self.access_token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
                self._save_tokens_to_cache()
                logger.info("✅ TokenManager: Токены успешно обновлены.")
            else:
                logger.error("❌ TokenManager: Ошибка обновления токена. Попытка полного входа.")
                await self.login()

async def get_user_info(token_manager: TokenManager) -> dict:
    """Получаем данные о пользователе, включая userHash и mHash."""
    await token_manager.refresh()  # Убедимся, что токены актуальны
    access_token = token_manager.access_token
    if not access_token:
        logger.error("❌ get_user_info: Нет access_token.")
        return None
    
    url = "https://api.dtf.ru/v2.31/subsite/me"
    headers = {
        "jwtauthorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            # Извлекаем данные из правильного места в JSON
            result_data = response.json().get("result", {})
            logger.info("✅ Данные пользователя успешно получены.")
            return result_data
        
        except Exception as e:
            logger.error("❌ get_user_info: Ошибка при получении или парсинге данных: %s", e, exc_info=True)
    
    logger.error("❌ get_user_info: Не удалось получить информацию о пользователе.")
    return None

async def send_comment(post_id: int, reply_to_id: int, text: str, token_manager: TokenManager) -> None:
    """Отправляет комментарий к посту.
    :param post_id: ID поста, к которому добавляется комментарий.
    :param text: Текст комментария.
    :param token_manager: Экземпляр TokenManager для управления токенами.
    """
    url = f"https://api.dtf.ru/v2.4/comment/add"
    headers = {
        "jwtauthorization": f"Bearer {token_manager.access_token}",
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"
    }
    payload = {
        "id": post_id,
        "text": text,
        "reply_to": reply_to_id
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            comment_id = response.json().get("result", {}).get("id")
            logger.info(f"✅ Комментарий успешно отправлен с ID {comment_id}.")
            return comment_id
        else:
            logger.error(f"❌ Ошибка при отправке комментария: {response.text}")
            return -1

async def delete_comment(comment_id: int, withThread: bool, token_manager: TokenManager) -> bool:
    """Удаляет комментарий по его ID.
    :param comment_id: ID комментария для удаления.
    :param withThread: Удалять ли ветку комментариев.
    :param token_manager: Экземпляр TokenManager для управления токенами.
    """
    url = f"https://api.dtf.ru/v3.0/comments/{comment_id}"
    headers = {
        "jwtauthorization": f"Bearer {token_manager.access_token}",
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"
    }
    params = {
        "withThread": withThread
    }

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers, params=params)
        if response.status_code == 200:
            logger.info(f"✅ Комментарий {comment_id} успешно удален.")
            return True
        else:
            logger.error(f"❌ Ошибка при удалении комментария {comment_id}: {response.text}")
            return False

async def get_subsite_posts(subsite_id: int, token_manager: TokenManager) -> list:
    """
    Получает список всех постов у подсайта/пользователя, используя итеративную загрузку.
    :param subsite_id: ID подсайта/пользователя.
    :param token_manager: Экземпляр TokenManager для управления токенами.
    """
    await token_manager.refresh()
    
    all_posts = []
    lastId = 0
    lastSortingValue = 0
    
    url = f"https://api.dtf.ru/v2.8/timeline"
    headers = {
        "jwtauthorization": f"Bearer {token_manager.access_token}",
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"
    }

    logger.info(f"Начинаю загрузку постов для пользователя {subsite_id}...")
    async with httpx.AsyncClient() as client:
        while True:
            params = {
                "subsitesIds": subsite_id,
                "sorting": "new",
                "markdown": "false",
                "lastId": lastId,
                "lastSortingValue": lastSortingValue,
            }
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                result = response.json().get("result", {})
                posts = result.get("items", [])
                
                if not posts:
                    logger.info("Больше постов не найдено, завершаю загрузку.")
                    break
                
                all_posts.extend(posts)
                logger.info(f"Загружено {len(all_posts)} постов...")

                # Обновляем значения для следующей итерации
                lastId = result.get("lastId")
                lastSortingValue = result.get("lastSortingValue")

            except httpx.HTTPStatusError as e:
                logger.error(f"Ошибка при получении постов: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                logger.error(f"Непредвиденная ошибка при загрузке постов: {e}", exc_info=True)
                break
                
    return all_posts

async def get_post_comments(post_id: int, token_manager: TokenManager) -> list:
    """Получает список комментариев к посту.
    :param post_id: ID поста.
    :param token_manager: Экземпляр TokenManager для управления токенами.
    """
    await token_manager.refresh()  # Убедимся, что токены актуальны
    url = f"https://api.dtf.ru/v2.9/comments"
    headers = {
        "jwtauthorization": f"Bearer {token_manager.access_token}",
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:137.0) Gecko/137.0 Firefox/137.0"
    }
    params = {
        "contentId": post_id,
        "sorting": "date",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("result", []).get("items", [])
            logger.info(f"✅ Получено {len(data)} комментариев к посту {post_id}.")
            return data
        else:
            logger.error(f"❌ Ошибка при получении комментариев к посту {post_id}: {response.text}")
            return []

async def find_and_delete_plus_users_comments(type: Literal['all_posts', 'one_post'], post_id: int | None, subsite_id: int | None, token_manager: TokenManager) -> int:
    """
    Ищет комментарии пользователей с подпиской Plus, после чего удаляем их.
    :param type: Тип поиска комментариев ('all_posts' для всех постов или 'one_post' для одного поста).
    :param post_id: ID поста, если type='one_post'.
    :param subsite_id: ID подсайта, если type='all_posts'.
    :param token_manager: Экземпляр TokenManager для управления токенами.
    """
    if (type == 'all_posts' and subsite_id is None) or (type == 'one_post' and post_id is None):
        logger.error("❌ Ошибка: Не указаны необходимые параметры для поиска комментариев.")
        return
    
    plus_comment_deleted_count = 0

    match type:
        case 'all_posts':
            logger.info("🔍 Поиск комментариев от Plus-пользователей во всех постах...")
            posts = await get_subsite_posts(subsite_id, token_manager=token_manager)
            for post in posts:
                post_id = post.get("id")
                plus_comment_deleted_count += await delete_all_comments_from_post(post_id,token_manager)
            return plus_comment_deleted_count

        case 'one_post':
            logger.info(f"🔍 Поиск комментариев от Plus-пользователей в посте {post_id}...")
            return await delete_all_comments_from_post(post_id,token_manager)

        case _:
            logger.error("❌ Ошибка: Неверный тип поиска комментариев. Используйте 'all_posts' или 'one_post'.")
            return -1

async def delete_all_comments_from_post(post_id: int, token_manager: TokenManager) -> int:
    comment_deleted_count = 0
    comments = await get_post_comments(post_id, token_manager)
    for comment in comments:
        user_plus_status = comment.get("author", {}).get("isPlus")
        username = comment.get("author", {}).get("name", "Неизвестный")
        if user_plus_status:
            await send_comment(post_id, comment.get("id"), f"{username}, здесь богатеям с подпиской Plus не рады! Отмени свою подписку - тогда поговорим. \n AntiDTFPlus - 'Сейчас запрещу людям с подпиской Plus писать под моими постами, так Комитет сразу все бесплатные функции вернет...'", token_manager)
            await delete_comment(comment.get("id"), withThread=False, token_manager=token_manager)
            comment_deleted_count += 1
    return comment_deleted_count