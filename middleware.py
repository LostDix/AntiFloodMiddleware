import logging, time
from collections import defaultdict
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from aiogram.exceptions import TelegramAPIError

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 5, interval: float = 10.0):
        """
        :param limit: Максимальное количество сообщений за интервал
        :param interval: Интервал времени в секундах
        """
        self.limit = limit
        self.interval = interval
        self.user_messages = defaultdict(list)
        super().__init__()
        logger.info(f"Initialized AntiFloodMiddleware with limit={limit}/per {interval}s")

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        try:
            # Определяем тип события
            real_event = None
            if event.message:
                real_event = event.message

            if real_event is None or not hasattr(real_event, 'from_user'):
                logger.debug("Unsupported event type, skipping flood check")
                return await handler(event, data)

            user_id = real_event.from_user.id
            current_time = time.time()

            # Очищаем старые сообщения
            self.user_messages[user_id] = [
                t for t in self.user_messages[user_id]
                if current_time - t < self.interval
            ]

            # Добавляем текущее событие
            self.user_messages[user_id].append(current_time)
            logger.debug(f"User {user_id} has {len(self.user_messages[user_id])} requests in last {self.interval}s")

            # Проверяем лимит
            if len(self.user_messages[user_id]) > self.limit:
                logger.warning(f"Flood detected from user {user_id} ({len(self.user_messages[user_id])} requests)")

                if isinstance(real_event, Message):
                    try:
                        await real_event.answer("⚠️ Слишком много запросов! Пожалуйста, подождите.")
                        logger.info(f"Sent flood warning to user {user_id}")
                    except TelegramAPIError as e:
                        logger.error(f"Failed to send flood warning: {str(e)}")

                return None

            return await handler(event, data)

        except Exception as e:
            logger.exception(f"Error in AntiFloodMiddleware: {str(e)}")
            return await handler(event, data)