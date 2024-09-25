import os

from app.engine.index import IndexConfig, get_index
from fastapi import HTTPException
from llama_index.core.callbacks import CallbackManager
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.settings import Settings


def get_chat_engine(filters=None, params=None, event_handlers=None):
    system_prompt = os.getenv("SYSTEM_PROMPT")
    top_k = int(os.getenv("TOP_K", "0"))

    llm = Settings.llm
    memory = ChatMemoryBuffer.from_defaults(
        token_limit=llm.metadata.context_window
    )
    callback_manager = CallbackManager(handlers=event_handlers or [])

    index_config = IndexConfig(callback_manager=callback_manager, **(params or {}))
    index = get_index(index_config)
    if index is None:
        raise HTTPException(
            status_code=500,
            detail=str(
                "StorageContext is empty - call 'poetry run generate' to generate the storage first"
            ),
        )

    retriever = index.as_retriever(
        filters=filters, **({"similarity_top_k": top_k} if top_k != 0 else {})
    )

    return CondensePlusContextChatEngine(
        llm=llm,
        memory=memory,
        system_prompt=system_prompt,
        retriever=retriever,
        callback_manager=callback_manager,
        verbose=True,
    )
