from abc import ABC, abstractmethod


class AIPlatform(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> str:
        pass #sends prompt to ai and returns response
