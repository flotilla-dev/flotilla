from abc import ABC, abstractmethod
from typing import Callable


class FlotillaTool(ABC):
    """
    API class for wrapping an LLM executable Tool.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The human readable name of the tool.  This name will be used in logging and error statements to identify the tool
        """
        ...

    @property
    @abstractmethod
    def llm_description(self) -> str:
        """
        A machine readable description of the Tool and how it works.  This description will be included to the LLM to assist in
        selecting a tool for execution by the LLM
        """
        ...

    @property
    @abstractmethod
    def execution_callable(self) -> Callable:
        """
        Returns the function that will be executed by the LLM.  Develoeprs are responsible for implementing the tool function and then
        returning that function via this method.
        """
        ...
