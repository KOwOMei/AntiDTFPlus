import asyncio
import json
import os
import httpx
import logging
import socketio
from typing import Literal

from .dtf_api import TokenManager, get_user_info, find_and_delete_plus_users_comments

# Настройка логгера
logger = logging.getLogger(__name__)

# Создаем клиент Socket.IO
sio = socketio.AsyncClient(reconnection=True, logger=True, engineio_logger=True)

async def start(token_manager: TokenManager, user_data: dict):
    """
    Запускает прослушивание упоминаний и кладет их в очередь.
    """
    DTF_WEBSOCKET_URL = "https://ws-sio.dtf.ru"
    user_hash = None
    m_hash = None

    # 1. Создаем функцию обратного вызова (callback)
    async def subscription_callback(status):
        """Эта функция будет вызвана, когда сервер ответит на нашу подписку."""
        logger.info("--- ОТВЕТ ОТ СЕРВЕРА НА ПОДПИСКУ ---")
        if status:
            logger.info("Сервер ответил со статусом: %s", status)
            if isinstance(status, dict) and status.get('status') == 'ok':
                logger.info("✅ Подписка на канал прошла успешно!")
            else:
                logger.warning("⚠️ Сервер ответил, но статус не 'ok'. Проверьте хэш или права.")
        else:
            logger.error("❌ Сервер не прислал статус в ответе. Возможно, подписка не удалась.")
        logger.info("------------------------------------")

    @sio.event
    async def connect():
        logger.info("Watcher: Соединение установлено. Подписываюсь на личный канал...")
        channel_name = f"mobile:{user_hash}"
        await sio.emit("subscribe", {"channel": channel_name}, callback=subscription_callback)

    @sio.on('event')
    async def message_handler(data):
        event_data = data.get("data", {})
        # Упоминание имеет тип 32
        if event_data.get("type") == 32:
            user_name = event_data.get("textParts", {}).get("subsite", {}).get("name")
            
            # Собираем информацию для обработки
            mention_info = {
                "user_name": user_name,
                "text": event_data.get("text", ""),
                "comment_id": event_data.get("data", {}).get("commentId"),
                "entry_id": event_data.get("data", {}).get("entryId"),
                "token_manager": token_manager
            }
            
              
    @sio.event
    async def disconnect():
        logger.info("Watcher: Отключен от сервера.")

    # 2. Добавляем аутентификацию в sio.connect()
    try:
        if not user_data:
            logger.error("Watcher: Не удалось получить информацию о пользователе. Завершение работы.")
            return
        logger.info("Watcher: Получен user_hash: %s", user_data['user_hash'])
        logger.info("Watcher: Получен m_hash: %s", user_data['m_hash'])
        user_hash = user_data['user_hash']
        m_hash = user_data['m_hash']
        logger.info("Watcher: Подключаюсь к WebSocket с JWT-аутентификацией...")
        await sio.connect(
            DTF_WEBSOCKET_URL,
            transports=['websocket']
        )
        await sio.wait()

    except Exception as e:
        logger.error("Watcher: Ошибка подключения или аутентификации: %s", e, exc_info=True)

async def main():
    # Создаем экземпляр TokenManager
    token_manager = TokenManager(email=None, password=None)
    
    # Получаем информацию о пользователе
    user_data = get_user_info(token_manager)

    if not user_data:
        print("Не удалось получить информацию о пользователе.")
        return

    # Создаем очередь для упоминаний
    await start(token_manager, user_data)
