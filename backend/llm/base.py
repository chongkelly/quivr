from abc import abstractmethod
from typing import AsyncIterable, List

from langchain.callbacks import AsyncCallbackHandler, AsyncIteratorCallbackHandler
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.llms import LLM

from logger import get_logger
from models.settings import BrainSettings  # Importing settings related to the 'brain'
from pydantic import BaseModel  # For data validation and settings management
from utils.constants import streaming_compatible_models

logger = get_logger(__name__)


class BaseBrainPicking(BaseModel):
    """
    Base Class for BrainPicking. Allows you to interact with LLMs (large language models)
    Use this class to define abstract methods and methods and properties common to all classes.
    """

    # Instantiate settings
    brain_settings = BrainSettings()

    # Default class attributes
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.0
    chat_id: str = None
    brain_id: str = None
    max_tokens: int = 256
    streaming: bool = False
    user_openai_api_key: str = None

    # the below functions define the logic for overwriting and defining the variables needed for this class.
    # openai_api_key
    def _determine_api_key(self, openai_api_key, user_openai_api_key):
        """If user provided an API key, use it."""
        if user_openai_api_key is not None:
            return user_openai_api_key
        else:
            return openai_api_key

    # streaming
    def _determine_streaming(self, model_name: str, streaming: bool) -> bool:
        """If the model name allows for streaming and streaming is declared, set streaming to True."""
        if model_name in streaming_compatible_models and streaming:
            return True
        else:
            return False

    # callbacks
    def _determine_callback_array(self, streaming) -> List[AsyncCallbackHandler]:
        """If streaming is set, set the AsyncIteratorCallbackHandler as the only callback."""
        if streaming:
            return [AsyncIteratorCallbackHandler]

    def __init__(self, **data):
        super().__init__(**data)

        self.openai_api_key = self._determine_api_key(
            self.brain_settings.openai_api_key, self.user_openai_api_key
        )
        self.streaming = self._determine_streaming(self.model_name, self.streaming)
        self.callbacks = self._determine_callback_array(self.streaming)

    class Config:
        """Configuration of the Pydantic Object"""

        # Allowing arbitrary types for class validation
        arbitrary_types_allowed = True

        # Util methods
        @staticmethod
        def format_chat_history(history) -> list[tuple[str, str]]:
            """Format the chat history into a list of tuples (human, ai)"""

            return [(chat.user_message, chat.assistant) for chat in history]

        # the below methods define the names, arguments and return types for the most useful functions for the child classes. These should be overwritten if they are used.
        @abstractmethod
        def _create_llm(self, model_name, streaming=False, callbacks=None) -> LLM:
            """
            Determine and construct the language model.
            :param model_name: Language model name to be used.
            :return: Language model instance

            This method should take into account the following:
            - Whether the model is streaming compatible
            - Whether the model is private
            - Whether the model should use an openai api key and use the _determine_api_key method
            """

        @abstractmethod
        def _create_question_chain(self, model_name) -> LLMChain:
            """
            Determine and construct the question chain.
            :param model_name: Language model name to be used.
            :return: Question chain instance

            This method should take into account the following:
            - Which prompt to use (normally CONDENSE_QUESTION_PROMPT)
            """

        @abstractmethod
        def _create_doc_chain(self, model_name) -> LLMChain:
            """
            Determine and construct the document chain.
            :param model_name Language model name to be used.
            :return: Document chain instance

            This method should take into account the following:
            - chain_type (normally "stuff")
            - Whether the model is streaming compatible and/or streaming is set (determine_streaming).
            """

        @abstractmethod
        def _create_qa(
            self, question_chain, document_chain
        ) -> ConversationalRetrievalChain:
            """
            Constructs a conversational retrieval chain .
            :param question_chain
            :param document_chain
            :return: ConversationalRetrievalChain instance
            """

        @abstractmethod
        def _call_chain(self, chain, question, history) -> str:
            """
            Call a chain with a given question and history.
            :param chain: The chain eg QA (ConversationalRetrievalChain)
            :param question: The user prompt
            :param history: The chat history from DB
            :return: The answer.
            """

        async def _acall_chain(self, chain, question, history) -> str:
            """
            Call a chain with a given question and history.
            :param chain: The chain eg qa (ConversationalRetrievalChain)
            :param question: The user prompt
            :param history: The chat history from DB
            :return: The answer.
            """
            raise NotImplementedError(
                "Async generation not implemented for this BrainPicking Class."
            )

        @abstractmethod
        def generate_answer(self, question: str) -> str:
            """
            Generate an answer to a given question using QA Chain.
            :param question: The question
            :return: The generated answer.

            This function should also call: _create_qa, get_chat_history and format_chat_history.
            It should also update the chat_history in the DB.
            """

        async def generate_stream(self, question: str) -> AsyncIterable:
            """
            Generate a streaming answer to a given question using QA Chain.
            :param question: The question
            :return: An async iterable which generates the answer.

            This function has to do some other things:
            - Update the chat history in the DB with the chat details(chat_id, question) -> Return a message_id and timestamp
            - Use the _acall_chain method inside create_task from asyncio to run the process on a child thread.
            - Append each token to the chat_history object from the db and yield it from the function
            - Append each token from the callback to an answer string -> Used to update chat history in DB (update_message_by_id)
            """
            raise NotImplementedError(
                "Async generation not implemented for this BrainPicking Class."
            )
