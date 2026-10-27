"""
Base AI Provider Interface
Defines the contract for all AI evaluation and chat reasoning engines.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseAIProvider(ABC):
    """
    Abstract AI Provider Interface.
    Ekansh: Extend this class to implement custom AI models (e.g. Gemini, Anthropic, DeepSeek).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider engine."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Indicates if this is a local mock provider or a live API."""
        pass

    @abstractmethod
    def generate_chat_response(
        self, prompt: str, subject: str = "Python Programming", history: List[Dict[str, str]] = None,
        learner_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates an educational, context-aware pedagogical response for the user.
        
        Returns:
            dict containing:
                - reply (str): Educational response
                - provider (str): Provider identifier
                - is_mock (bool): Mock status flag
                - suggested_followups (List[str]): List of relevant follow-up prompts
        """
        pass

    @abstractmethod
    def evaluate_assessment(
        self,
        subject: str,
        questions: List[Dict[str, Any]],
        user_answers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Evaluates a 5-question assessment deterministically or via LLM evaluation.
        
        Returns:
            dict containing:
                - score (int): Number of correct answers out of 5
                - total (int): Total questions (5)
                - percentage (float): Score percentage (0.0 - 100.0)
                - proficiency_level (str): 'Beginner' | 'Intermediate' | 'Advanced'
                - breakdown (List[dict]): Itemized question review with explanation
                - recommended_topics (List[str]): Targeted next learning topics
                - summary_feedback (str): Comprehensive performance feedback
                - is_mock (bool): True if evaluated by mock engine
                - provider (str): Provider identifier
        """
        pass
