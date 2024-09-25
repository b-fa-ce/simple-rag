import logging
from llama_index.core.readers import SimpleDirectoryReader

from app.config import DATA_DIR

logger = logging.getLogger(__name__)


def get_file_documents():

    try:
        file_extractor = None
        reader = SimpleDirectoryReader(
            DATA_DIR,
            recursive=True,
            filename_as_id=True,
            raise_on_error=True,
            file_extractor=file_extractor,
        )
        return reader.load_data()
    except FileNotFoundError as e:
        # Handle FileNotFoundError
        logger.error("File not found: %s", e)
    except IsADirectoryError as e:
        # Handle IsADirectoryError
        logger.error("Is a directory: %s", e)
    except PermissionError as e:
        # Handle PermissionError
        logger.error("Permission denied: %s", e)
    except Exception as e:
        # Handle other exceptions
        logger.error("An error occurred: %s", e)
        import sys
        import traceback

        # Catch the error if the data dir is empty
        # and return as empty document list
        _, _, exc_traceback = sys.exc_info()
        function_name = traceback.extract_tb(exc_traceback)[-1].name
        if function_name == "_add_files":
            logger.warning(
                "Failed to load file documents, error message: %s . Return as empty document list.",
                e
            )
            return []
        else:
            # Raise the error if it is not the case of empty data dir
            raise e
