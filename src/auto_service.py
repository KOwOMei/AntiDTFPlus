import asyncio
import logging
import socketio
import os
import servicemanager
import win32event
import win32service
import win32serviceutil
import threading

from .dtf_api import TokenManager, get_user_info, find_and_delete_plus_users_comments

log_dir = os.path.join(os.path.expanduser("~"), ".antidtfplus")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "service.log")),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

class WebSocketWatcher:
    """
    Класс для управления WebSocket соединением и обработкой событий.
    """
    DTF_WEBSOCKET_URL = "https://ws-sio.dtf.ru"

    def __init__(self, token_manager: TokenManager, user_data: dict):
        self.token_manager = token_manager
        self.user_hash = user_data.get('user_hash')
        self.sio = socketio.AsyncClient(reconnection=True, logger=True, engineio_logger=True)
        self._setup_events()

    def _setup_events(self):
        """Настройка обработчиков событий для Socket.IO."""
        @self.sio.event
        async def connect():
            logger.info("Watcher: Соединение установлено. Подписываюсь на личный канал...")
            channel_name = f"mobile:{self.user_hash}"
            await self.sio.emit("subscribe", {"channel": channel_name}, callback=self.subscription_callback)

        @self.sio.on('event')
        async def message_handler(data):
            event_data = data.get("data", {})
            # Упоминание имеет тип 8
            if event_data.get("type") == 8:
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
            logger.info("Watcher: Отключен от сервера.")

    async def subscription_callback(self, status):
        """Callback для ответа на подписку."""
        logger.info("--- ОТВЕТ ОТ СЕРВЕРА НА ПОДПИСКУ ---")
        if isinstance(status, dict) and status.get('status') == 'ok':
            logger.info("✅ Подписка на канал прошла успешно!")
        else:
            logger.warning(f"⚠️ Статус подписки не 'ok'. Ответ: {status}")
        logger.info("------------------------------------")

    async def start(self):
        """Запускает подключение к WebSocket."""
        if not self.user_hash:
            logger.error("Watcher: Отсутствует user_hash. Невозможно запустить.")
            return
        
        try:
            logger.info("Watcher: Подключаюсь к WebSocket...")
            await self.sio.connect(
                self.DTF_WEBSOCKET_URL,
                transports=['websocket']
            )
            await self.sio.wait()
        except Exception as e:
            logger.error(f"Watcher: Ошибка подключения: {e}", exc_info=True)

async def main_async(stop_event):
    """
    Основная асинхронная логика, которая теперь может быть остановлена.
    """
    logger.info("Запуск асинхронной части сервиса AntiDTFPlus...")
    token_manager = TokenManager()

    if not token_manager.refresh_token:
        logger.error("RefreshToken не найден. Невозможно запустить сервис. Запустите GUI для входа.")
        return

    while not stop_event.is_set():
        try:
            await token_manager.refresh()
            if not token_manager.access_token:
                logger.error("Не удалось обновить токен. Повторная попытка через 5 минут.")
                await asyncio.sleep(300)
                continue
            
            logger.info("Токен успешно обновлен.")

            # Получаем информацию о пользователе
            user_data = await get_user_info(token_manager)
            if not user_data:
                logger.error("Не удалось получить информацию о пользователе. Повторная попытка через 5 минут.")
                await asyncio.sleep(300)
                continue
            
            logger.info(f"Получена информация для пользователя: {user_data.get('name')}")

            watcher = WebSocketWatcher(token_manager, user_data)
            
            watcher_task = asyncio.create_task(watcher.start())
            stop_wait_task = asyncio.create_task(asyncio.to_thread(stop_event.wait))
            
            done, pending = await asyncio.wait(
                [watcher_task, stop_wait_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if stop_event.is_set():
                logger.info("Получен сигнал остановки сервиса.")
                if watcher.sio.connected:
                    await watcher.sio.disconnect()
                break 

        except Exception as e:
            logger.error(f"Произошла критическая ошибка в главном цикле: {e}", exc_info=True)
            logger.info("Перезапуск через 1 минуту...")
            await asyncio.sleep(60)


class AntiDTFPlusService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'AntiDTFPlusService'
    _svc_display_name_ = 'AntiDTFPlus Auto-Start Service'
    _svc_description_ = 'Отслеживает упоминания в комментариях DTF и удаляет комментарии от пользователей с DTF Plus.'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socketio.client.logger.setLevel(logging.WARNING)
        socketio.client.engineio.setLevel(logging.WARNING)
        self.stop_event = threading.Event()
        self.thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info('Получен сигнал остановки сервиса...')
        self.stop_event.set()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        self.thread = threading.Thread(target=self.main_thread_func)
        self.thread.start()

        logger.info('Сервис запущен, основной поток ожидает сигнала остановки.')
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        logger.info('Сигнал остановки обработан, завершаю SvcDoRun.')

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
