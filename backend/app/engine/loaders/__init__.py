import yaml
from app.engine.loaders.file import get_file_documents


def load_configs():
    with open("config/loaders.yaml") as f:
        configs = yaml.safe_load(f)
    return configs


def get_documents():
    documents = []
    config = load_configs()
    for loader_type in config.items():

        match loader_type:
            case "file":
                document = get_file_documents()
            case _:
                raise ValueError(f"Invalid loader type: {loader_type}")
        documents.extend(document)

    return documents
