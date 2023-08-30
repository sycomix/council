from abc import ABC, abstractmethod
from typing import List

from council.contexts import AgentContext, ScoredChatMessage
from council.runners import Budget


class EvaluatorBase(ABC):
    """
    Abstract base class for an agent evaluator.

    """

    def execute(self, context: AgentContext, budget: Budget) -> List[ScoredChatMessage]:
        """
        Executes the evaluator on the agent's context within the given budget.

        Args:
            context (AgentContext): The context for executing the evaluator.
            budget (Budget): The budget for evaluator execution.

        Returns:
            List[ScoredChatMessage]: A list of scored agent messages resulting from the evaluation.

        Raises:
            None
        """
        return self._execute(context=context, budget=budget)

    @abstractmethod
    def _execute(self, context: AgentContext, budget: Budget) -> List[ScoredChatMessage]:
        pass
