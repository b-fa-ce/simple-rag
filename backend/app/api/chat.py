import logging


from app.api.routers.vercel_response import VercelStreamResponse
from fastapi import APIRouter, Depends, HTTPException, status, Request
from llama_index.core.chat_engine.types import BaseChatEngine
from llama_index.core.llms import MessageRole

from app.engine.engine import get_chat_engine
from app.api.models import Message, Result, SourceNodes, ChatData


chat_router = chatr = APIRouter()

logger = logging.getLogger("uvicorn")


# non-streaming endpoint
@chatr.post("/request")
async def chat_request(
    data: ChatData,
    chat_engine: BaseChatEngine = Depends(get_chat_engine),
) -> Result:
    last_message_content = data.get_last_message_content()
    messages = data.get_history_messages()

    logger.info("last_message_content: %s", last_message_content)

    response = await chat_engine.achat(last_message_content, messages)

    return Result(
        result=Message(role=MessageRole.ASSISTANT, content=response.response),
        nodes=SourceNodes.from_source_nodes(response.source_nodes),
    )


# streaming endpoint
@chatr.post("")
async def chat(
    request: Request,
    data: ChatData,
):
    try:
        last_message_content = data.get_last_message_content()
        messages = data.get_history_messages()

        params = data.data or {}

        chat_engine = get_chat_engine(params=params)

        response = await chat_engine.astream_chat(last_message_content, messages)

        return VercelStreamResponse(request, response)
    except Exception as e:
        logger.exception("Error in chat engine", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chat engine: {e}",
        ) from e
