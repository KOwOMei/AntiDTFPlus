import asyncio
import logging
import socketio
import servicemanager
import win32event
import win32service
import win32serviceutil
import threading
import os

from .dtf_api import TokenManager, get_user_info, find_and_delete_plus_users_comments
from .log_config import setup_logging

# Настраиваем логирование один раз при импорте модуля
setup_logging()
logger = logging.getLogger(__name__)

class WebSocketWatcher:
    """
    Класс для управления WebSocket соединением. Стал проще, так как получает
    токен и user_hash напрямую, а не целый token_manager.
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
            await self.sio.wait() # Эта строка будет работать, пока есть соединение
        except socketio.exceptions.ConnectionError as e:
            logger.error(f"Watcher: Ошибка подключения: {e}. Повторная попытка через 60 секунд.")
        finally:
            if self.sio.connected:
                await self.sio.disconnect()
            logger.info("Watcher: Соединение завершено.")


async def main_async(stop_event: threading.Event):
    """
    Упрощенная основная асинхронная логика.
    Получает данные один раз, затем входит в цикл поддержания соединения.
    """
    logger.info("Запуск асинхронной части сервиса...")
    token_manager = TokenManager()

    # 1. Получаем токен и данные пользователя ОДИН РАЗ при запуске
    try:
        if not token_manager.refresh_token:
            logger.error("RefreshToken не найден. Запустите GUI для входа.")
            return

        user_data = await get_user_info(token_manager)
        user_hash = user_data.get('userHash')

        # ИСПРАВЛЕНИЕ: Проверяем, что user_hash получен
        if not user_hash:
            logger.error(f"Не удалось получить 'user_hash' из данных пользователя: {user_data}")
            return
        
        logger.info(f"Успешно получены данные для пользователя: {user_data.get('name')} (hash: ...{user_hash[-4:]})")
        watcher = WebSocketWatcher(token_manager, user_hash)

    except Exception as e:
        logger.critical(f"Критическая ошибка при инициализации: {e}", exc_info=True)
        return

    # 2. Основной цикл: поддерживает работу watcher'а и проверяет сигнал остановки
    while not stop_event.is_set():
        try:
            # Запускаем watcher. Эта задача завершится только при разрыве соединения.
            await watcher.start()
            
            # Если watcher завершил работу (разрыв связи), ждем перед переподключением
            if not stop_event.is_set():
                logger.info("Ожидание 60 секунд перед попыткой переподключения...")
                await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Непредвиденная ошибка в главном цикле: {e}", exc_info=True)
            if not stop_event.is_set():
                await asyncio.sleep(60)
    
    logger.info("Получен сигнал остановки. Завершаю асинхронные задачи...")
    if watcher.sio.connected:
        await watcher.sio.disconnect()
    logger.info("Асинхронная часть сервиса остановлена.")


class AntiDTFPlusService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'AntiDTFPlusService'
    _svc_display_name_ = 'AntiDTFPlus Auto-Start Service'
    _svc_description_ = 'Отслеживает упоминания и удаляет комментарии от пользователей с DTF Plus.'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stop_event = threading.Event()
        self.thread = None
        # Убираем лишние логи из библиотек
        logging.getLogger('socketio').setLevel(logging.WARNING)
        logging.getLogger('engineio').setLevel(logging.WARNING)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info('Получен сигнал остановки сервиса, передаю в рабочий поток...')
        self.stop_event.set()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        try:
            self.thread = threading.Thread(target=self.main_thread_func)
            self.thread.start()

            logger.info('Сервис запущен, основной поток ожидает сигнала остановки.')
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            logger.info('Сигнал остановки обработан, завершаю SvcDoRun.')
        except Exception as e:
            logger.error(f"Service: Критическая ошибка в SvcDoRun: {e}", exc_info=True)
            logger.info("Перезапуск службы из-за ошибки...")
            os._exit(1)

    def main_thread_func(self):
        """Эта функция будет выполняться в отдельном потоке."""
        logger.info("Запуск рабочего потока сервиса.")
        try:
            asyncio.run(main_async(self.stop_event))
        except Exception as e:
            logger.error(f"Критическая ошибка в рабочем потоке сервиса: {e}", exc_info=True)
        
        logger.info("Рабочий поток сервиса завершен.")


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AntiDTFPlusService)
