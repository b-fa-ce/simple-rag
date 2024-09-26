import json

from aiostream import stream
from app.api.models import SourceNodes
from fastapi import Request
from fastapi.responses import StreamingResponse
from llama_index.core.chat_engine.types import StreamingAgentChatResponse


class VercelStreamResponse(StreamingResponse):
    """
    Class to convert the response from the chat engine to the streaming format expected by Vercel
    """

    TEXT_PREFIX = "0:"
    DATA_PREFIX = "8:"

    @classmethod
    def convert_text(cls, token: str):
        # Escape newlines and double quotes to avoid breaking the stream
        token = json.dumps(token)
        return f"{cls.TEXT_PREFIX}{token}\n"

    @classmethod
    def convert_data(cls, data: dict):
        data_str = json.dumps(data)
        return f"{cls.DATA_PREFIX}[{data_str}]\n"

    def __init__(
        self,
        request: Request,
        response: StreamingAgentChatResponse,
      ):
        content = VercelStreamResponse.content_generator(request, response)
        super().__init__(content=content)

    @classmethod
    async def content_generator(
        cls,
        request: Request,
        response: StreamingAgentChatResponse,
    ):
        # Yield the text response
        async def _chat_response_generator():
            final_response = ""
            async for token in response.async_response_gen():
                final_response += token
                yield cls.convert_text(token)

            # Yield the source nodes
            yield cls.convert_data(
                {
                    "type": "sources",
                    "data": {
                        "nodes": [
                            SourceNodes.from_source_node(node).model_dump()
                            for node in response.source_nodes
                        ]
                    },
                }
            )

        combine = stream.merge(_chat_response_generator())
        is_stream_started = False
        async with combine.stream() as streamer:
            async for output in streamer:
                if not is_stream_started:
                    is_stream_started = True
                    # Stream a blank message to start the stream
                    yield cls.convert_text("")

                yield output

                if await request.is_disconnected():
                    break
