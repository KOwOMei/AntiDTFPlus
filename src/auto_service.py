import asyncio
import logging
import socketio
import os
import sys

from .dtf_api import TokenManager, get_user_info, find_and_delete_plus_users_comments
from .log_config import setup_logging

# Настраиваем логирование один раз при импорте модуля
setup_logging()
logger = logging.getLogger(__name__)

class WebSocketWatcher:
    """
    Класс для управления WebSocket соединением. Код остается без изменений.
    """
    DTF_WEBSOCKET_URL = "https://ws-sio.dtf.ru"

    def __init__(self, token_manager: TokenManager, user_hash: str):
        self.token_manager = token_manager
        self.user_hash = user_hash
        self.sio = socketio.AsyncClient(reconnection=True, logger=True, engineio_logger=True)
        self._setup_events()

    def _setup_events(self):
        @self.sio.event
        async def connect():
            logger.info("Watcher: Соединение установлено. Подписываюсь на личный канал...")
            channel_name = f"mobile:{self.user_hash}"
            await self.sio.emit("subscribe", {"channel": channel_name}, callback=self.subscription_callback)

        @self.sio.on('event')
        async def message_handler(data):
            event_data = data.get("data", {})
            if event_data.get("type") == 8: # Упоминание
                comment_data = event_data.get("data", {})
                entry_id = comment_data.get("entryId")
                comment_id = comment_data.get("commentId")
                logger.info(f"Получено упоминание в посте {entry_id}, комментарий {comment_id}")
                if entry_id and comment_id:
                    try:
                        await find_and_delete_plus_users_comments('one_post', entry_id, None, self.token_manager)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке упоминания: {e}", exc_info=True)

        @self.sio.event
        async def disconnect():
            logger.warning("Watcher: Отключен от сервера. Попытка переподключения...")

    async def subscription_callback(self, status):
        if isinstance(status, dict) and status.get('status') == 'ok':
            logger.info("✅ Подписка на канал прошла успешно!")
        else:
            logger.warning(f"⚠️ Статус подписки не 'ok'. Ответ: {status}")

    async def start(self):
        """Запускает и поддерживает подключение к WebSocket."""
        try:
            logger.info("Watcher: Подключаюсь к WebSocket...")
            await self.sio.connect(self.DTF_WEBSOCKET_URL, transports=['websocket'])
            await self.sio.wait()
        except socketio.exceptions.ConnectionError as e:
            logger.error(f"Watcher: Ошибка подключения: {e}. Повторная попытка через 60 секунд.")
        finally:
            if self.sio.connected:
                await self.sio.disconnect()
            logger.info("Watcher: Соединение завершено.")

async def main_async():
    """
    Основная асинхронная логика. Теперь не принимает stop_event.
    """
    logger.info("Запуск фонового процесса...")
    token_manager = TokenManager()

    try:
        if not token_manager.refresh_token:
            logger.error("RefreshToken не найден. Запустите GUI для входа.")
            return

        await token_manager.refresh()
        user_data = await get_user_info(token_manager)
        user_hash = user_data.get('userHash')

        if not user_hash:
            logger.error(f"Не удалось получить 'userHash': {user_data}")
            return
        
        logger.info(f"Успешно получены данные для пользователя: {user_data.get('name')}")
        watcher = WebSocketWatcher(token_manager, user_hash)

    except Exception as e:
        logger.critical(f"Критическая ошибка при инициализации: {e}", exc_info=True)
        return

    # Основной цикл: просто перезапускает watcher при разрыве связи
    while True:
        try:
            await watcher.start()
            logger.info("Ожидание 60 секунд перед попыткой переподключения...")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в главном цикле: {e}", exc_info=True)
            await asyncio.sleep(60)


if __name__ == '__main__':
    # Устанавливаем рабочую директорию, чтобы находить файлы (например, токен)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
        
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Процесс прерван пользователем.")
    except Exception as e:
        logger.critical(f"Фатальная ошибка в приложении: {e}", exc_info=True)
