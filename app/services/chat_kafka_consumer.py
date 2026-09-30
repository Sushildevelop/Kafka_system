import asyncio
import json
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from app.core.config import Settings
from app.repositories.study_group_repository import StudyGroupRepository
from app.schemas.study_group import GroupChatMessageEvent
from app.services.chat_manager import GroupChatConnectionManager
from app.services.study_group_service import process_chat_event
from app.utils.logger import get_logger
logger=get_logger(__name__); CHAT_TOPIC="study-group-chat"
class StudyGroupChatConsumer:
    """Consumes every chat event for local WebSocket fan-out."""
    def __init__(self,settings:Settings,repository:StudyGroupRepository,manager:GroupChatConnectionManager)->None:
        self._settings=settings; self._repository=repository; self._manager=manager; self._consumer=None; self._task=None
    async def start(self)->None:
        consumer=AIOKafkaConsumer(CHAT_TOPIC,bootstrap_servers=self._settings.kafka_bootstrap_servers,group_id=self._settings.kafka_chat_consumer_group,auto_offset_reset="latest",enable_auto_commit=False,request_timeout_ms=5000)
        try: await consumer.start()
        except (KafkaError,OSError): logger.exception("Study group chat consumer could not connect"); return
        self._consumer=consumer; self._task=asyncio.create_task(self._consume(),name="study-group-chat-consumer")
    async def _consume(self)->None:
        if self._consumer is None: return
        while True:
            try:
                message=await self._consumer.getone(); event=GroupChatMessageEvent.model_validate(json.loads(message.value.decode("utf-8")))
                await process_chat_event(event,self._repository,self._manager); await self._consumer.commit()
            except asyncio.CancelledError: raise
            except (ValueError,TypeError): logger.exception("Invalid study group chat event"); await self._consumer.commit()
            except Exception: logger.exception("Study group chat processing failed; retrying"); await asyncio.sleep(1)
    async def stop(self)->None:
        if self._task is not None:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
            self._task=None
        if self._consumer is not None: await self._consumer.stop(); self._consumer=None
