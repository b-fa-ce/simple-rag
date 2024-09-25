import logging
import os
from datetime import timedelta
from typing import Optional

from llama_index.core.callbacks import CallbackManager
from llama_index.core.indices import load_index_from_storage
from llama_index.core.storage import StorageContext
from pydantic import BaseModel, Field
from cachetools import cached, TTLCache

logger = logging.getLogger("uvicorn")


class IndexConfig(BaseModel):
    callback_manager: Optional[CallbackManager] = Field(
        default=None,
    )


def get_index(config: IndexConfig = None):
    if config is None:
        config = IndexConfig()
    storage_dir = os.getenv("STORAGE_DIR", "storage")
    # check if storage already exists
    if not os.path.exists(storage_dir):
        return None
    # load the existing index
    logger.info("Loading index from %s...", storage_dir)
    storage_context = get_storage_context(storage_dir)
    index = load_index_from_storage(
        storage_context, callback_manager=config.callback_manager
    )
    logger.info("Finished loading index from %s", storage_dir)
    return index


@cached(
    TTLCache(maxsize=10, ttl=timedelta(minutes=5).total_seconds()),
    key=lambda *args, **kwargs: "global_storage_context",
)
def get_storage_context(persist_dir: str) -> StorageContext:
    return StorageContext.from_defaults(persist_dir=persist_dir)
