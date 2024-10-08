import logging
import os
from typing import Any, Dict, List, Literal, Optional

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import NodeWithScore
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from app.config import DATA_DIR

logger = logging.getLogger("uvicorn")


class FileContent(BaseModel):
    """
    Represents the content of a file.

    Attributes:
      type (Literal["text", "ref"]): The type of the file content. It can be either "text" or "ref".
      value (str | List[str]): The value of the file content. If the file is pure text, it is a string. Otherwise, it is a list of document IDs.
    """
    type: Literal["text", "ref"]
    # If the file is pure text then the value is be a string
    # otherwise, it's a list of document IDs
    value: str | List[str]


class File(BaseModel):
    """
    Represents a file.

    Attributes:
      id (str): The ID of the file.
      content (FileContent): The content of the file.
      filename (str): The name of the file.
      filesize (int): The size of the file in bytes.
      filetype (str): The type of the file.
    """
    id: str
    content: FileContent
    filename: str
    filesize: int
    filetype: str


class AnnotationFileData(BaseModel):
    """
    Model representing annotation file data.

    Attributes:
      files (List[File]): List of files.

    Config:
      json_schema_extra (dict): Extra JSON schema for the model.
        example (dict): Example data for the model.
          csvFiles (list): List of CSV files.
            content (str): Content of the file.
            filename (str): Name of the file.
            filesize (int): Size of the file.
            id (str): ID of the file.
            type (str): Type of the file.
      alias_generator (callable): Alias generator function.
    """
    files: List[File] = Field(
        default=[],
        description="List of files",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "csvFiles": [
                    {
                        "content": "Name, Age\nAlice, 25\nBob, 30",
                        "filename": "example.csv",
                        "filesize": 123,
                        "id": "123",
                        "type": "text/csv",
                    }
                ]
            }
        }
        alias_generator = to_camel


class Annotation(BaseModel):
    """
    Represents an annotation.

    Attributes:
      type (str): The type of the annotation.
      data (AnnotationFileData | List[str]): The data associated with the annotation.

    Methods:
      to_content() -> str | None:
        Converts the annotation to content.

        Returns:
          str | None: The generated content if successful, None otherwise.
    """
    type: str
    data: AnnotationFileData | List[str]

    def to_content(self) -> str | None:
        """
        Generates context content based on the type of annotation.

        Returns:
          str | None: The generated context content or None if the annotation type is not supported.
        """
        if self.type == "document_file":
            # We only support generating context content for CSV files for now
            csv_files = [file for file in self.data.files if file.filetype == "csv"]
            if len(csv_files) > 0:
                return "Use data from following CSV raw content\n" + "\n".join(
                    [f"```csv\n{csv_file.content.value}\n```" for csv_file in csv_files]
                )
        else:
            logger.warning(
                "The annotation %s is not supported for generating context content",
                self.type,
            )
        return None


class Message(BaseModel):
    """
    Message class represents a message with role, content, and optional annotations.

    Attributes:
      role (MessageRole): The role of the message.
      content (str): The content of the message.
      annotations (List[Annotation], optional): The list of annotations associated with the message, if any.
    """
    role: MessageRole
    content: str
    annotations: List[Annotation] | None = None


class ChatData(BaseModel):
    messages: List[Message]
    data: Any = None

    class Config:
        """
        Configuration class for the ChatData.

        Attributes:
          json_schema_extra (dict): Extra JSON schema for the model.

        Example:
        """
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "What standards for letters exist?",
                    }
                ]
            }
        }


    def get_last_message_content(self) -> str:
        """
        Get the content of the last message along with the data content if available.
        Fallback to use data content from previous messages
        """
        if len(self.messages) == 0:
            raise ValueError("There is not any message in the chat")
        last_message = self.messages[-1]
        message_content = last_message.content
        for message in reversed(self.messages):
            if message.role == MessageRole.USER and message.annotations is not None:
                annotation_contents = filter(
                    None,
                    [annotation.to_content() for annotation in message.annotations],
                )
                if not annotation_contents:
                    continue
                annotation_text = "\n".join(annotation_contents)
                message_content = f"{message_content}\n{annotation_text}"
                break
        return message_content

    def get_history_messages(self) -> List[ChatMessage]:
        """
        Get the history messages
        """
        return [
            ChatMessage(role=message.role, content=message.content)
            for message in self.messages[:-1]
        ]

    def is_last_message_from_user(self) -> bool:
        return self.messages[-1].role == MessageRole.USER

    def get_chat_document_ids(self) -> List[str]:
        """
        Get the document IDs from the chat messages
        """
        document_ids: List[str] = []
        for message in self.messages:
            if message.role == MessageRole.USER and message.annotations is not None:
                for annotation in message.annotations:
                    if (
                        annotation.type == "document_file"
                        and annotation.data.files is not None
                    ):
                        for fi in annotation.data.files:
                            if fi.content.type == "ref":
                                document_ids += fi.content.value
        return list(set(document_ids))


class SourceNodes(BaseModel):
    id: str
    metadata: Dict[str, Any]
    score: Optional[float]
    text: str
    url: Optional[str]

    @classmethod
    def from_source_node(cls, source_node: NodeWithScore):
        metadata = source_node.node.metadata
        url = cls.get_url_from_metadata(metadata)

        return cls(
            id=source_node.node.node_id,
            metadata=metadata,
            score=source_node.score,
            text=source_node.node.text,  # type: ignore
            url=url,
        )

    @classmethod
    def get_url_from_metadata(cls, metadata: Dict[str, Any]) -> str:
        url_prefix = os.getenv("FILESERVER_URL_PREFIX")
        if not url_prefix:
            logger.warning(
                "Warning: FILESERVER_URL_PREFIX not set in environment variables. Can't use file server"
            )
        file_name = metadata.get("file_name")

        if file_name and url_prefix:
            # file_name exists and file server is configured
            pipeline_id = metadata.get("pipeline_id")
            if pipeline_id:
                # file is from LlamaCloud
                file_name = f"{pipeline_id}${file_name}"
                return f"{url_prefix}/output/llamacloud/{file_name}"
            is_private = metadata.get("private", "false") == "true"
            if is_private:
                # file is a private upload
                return f"{url_prefix}/output/uploaded/{file_name}"
            # file is from calling the 'generate' script
            # Get the relative path of file_path to data_dir
            file_path = metadata.get("file_path")
            data_dir = os.path.abspath(DATA_DIR)
            if file_path and data_dir:
                relative_path = os.path.relpath(file_path, data_dir)
                return f"{url_prefix}/data/{relative_path}"
        # fallback to URL in metadata (e.g. for websites)
        return metadata.get("URL")

    @classmethod
    def from_source_nodes(cls, source_nodes: List[NodeWithScore]):
        return [cls.from_source_node(node) for node in source_nodes]


class Result(BaseModel):
    result: Message
    nodes: List[SourceNodes]


class ChatConfig(BaseModel):
    starter_questions: Optional[List[str]] = Field(
        default=None,
        description="List of starter questions",
        serialization_alias="starterQuestions",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "starterQuestions": [
                    "What standards for letters exist?",
                    "What are the requirements for a letter to be considered a letter?",
                ]
            }
        }
