import logging

from fastapi import APIRouter, Depends
from llama_index.core.chat_engine.types import BaseChatEngine
from llama_index.core.llms import MessageRole

from app.engine.engine import get_chat_engine
from app.api.models import Message, Result, SourceNodes, ChatData


chat_router = chatr = APIRouter()

logger = logging.getLogger("uvicorn")


# non-streaming endpoint - delete if not needed
@chatr.post("/request")
async def chat_request(
    data: ChatData,
    chat_engine: BaseChatEngine = Depends(get_chat_engine),
) -> Result:
    last_message_content = data.get_last_message_content()
    messages = data.get_history_messages()

    logger.info("last_message_content: %s", last_message_content)

    response = await chat_engine.achat(last_message_content, messages)
    # respones2 = chat_engine.query(last_message_content)

    print("response", response)# respones2)

    return Result(
        result=Message(role=MessageRole.ASSISTANT, content=response.response),
        nodes=SourceNodes.from_source_nodes(response.source_nodes),
    )
