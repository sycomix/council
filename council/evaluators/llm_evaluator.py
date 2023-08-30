"""
LLMEvaluator implementation.

This evaluator uses the given `LLM` to evaluate the chain's responses.
"""
import logging
from typing import List

from council.contexts import AgentContext, ScoredChatMessage, ChatMessage
from council.evaluators import EvaluatorBase
from council.llm import LLMBase, LLMMessage
from council.runners import Budget
from council.utils import Option

logger = logging.getLogger(__name__)


class LLMEvaluator(EvaluatorBase):
    """Evaluator using an `LLM` to evaluate chain responses."""

    def __init__(self, llm: LLMBase):
        """
        Build a new LLMEvaluator.

        :param llm: model to use for the evaluation.
        """
        super().__init__()
        self._llm = llm

    def _execute(self, context: AgentContext, budget: Budget) -> List[ScoredChatMessage]:
        query = context.chatHistory.try_last_user_message.unwrap()
        chain_results = [
            chain_history[-1].try_last_message.unwrap()
            for chain_history in context.chainHistory.values()
            if chain_history[-1].try_last_message.is_some()
        ]

        # Build prompt to send to the inner LLM
        llm_response = self._call_llm(query, chain_results, budget)

        # Parse LLM response with the score for each message we want to score
        scores = [self._parse_eval(line) for line in llm_response.split("\n") if line.lower().startswith("grade")]

        scored_messages = []
        for skill_message, score in filter(lambda tuple: tuple[1].is_some(), zip(chain_results, scores)):
            scored_message = ScoredChatMessage(
                ChatMessage.agent(message=skill_message.message, data=skill_message.data), score.unwrap()
            )
            scored_messages.append(scored_message)

        return scored_messages

    def _call_llm(self, query: ChatMessage, chain_results: list[ChatMessage], budget: Budget) -> str:
        messages = self._build_llm_messages(query, chain_results)
        if len(messages) <= 0:
            return ""

        result = self._llm.post_chat_request(messages=messages)
        for c in result.consumptions:
            budget.add_consumption(c, self.__class__.__name__)
        llm_response = result.first_choice
        logger.debug(f"llm response: {llm_response}")
        return llm_response

    def _build_llm_messages(self, query: ChatMessage, skill_messages: list[ChatMessage]) -> List[LLMMessage]:
        if len(skill_messages) <= 0:
            return []

        if len(skill_messages) == 1:
            prompt = self._build_system_prompt_single_answer()
            return [
                LLMMessage.system_message(prompt),
                LLMMessage.user_message(self._build_single_answer_message(query.message, skill_messages[0].message)),
            ]

        responses = [skill_message.message for skill_message in skill_messages]
        prompt = self._build_system_prompt_multiple_answers()
        return [
            LLMMessage.system_message(prompt),
            LLMMessage.user_message(self._build_multiple_answers_message(query.message, responses)),
        ]

    @staticmethod
    def _parse_eval(line: str) -> Option[float]:
        """Parse the evaluation response from the inner `LLM`."""

        line = line.lower().removeprefix("answer").strip().replace("-", ":")
        try:
            score = line.split(":", 3)
            return Option.some(float(score[1]))
        except ValueError:
            logging.exception(f'message="could not parse score" line="{line}"')
            raise
        except Exception:
            logging.exception(f'message="could not parse evaluation response" line="{line}"')
            raise

    @staticmethod
    def _build_multiple_answers_message(query: str, answers: list[str]) -> str:
        prompt_answers = "\n".join(f"Answer #{index+1} is:\n{answer}" for index, answer in enumerate(answers))
        lines = ["# The question to grade is:", query, "# The given answers are:", prompt_answers, "# Please grade."]
        return "\n".join(lines)

    @staticmethod
    def _build_single_answer_message(query: str, answer: str) -> str:
        lines = ["# The question to grade is:", query, "# The given answer is:", answer, "# Please grade."]
        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt_multiple_answers() -> str:
        """Build prompt that will be sent to the inner `LLM`."""
        task_description = [
            "# You are a grading expert, grading how accurate and relevant multiple answers are to a given question.",
            "# Your grade will only be based on the given answer.",
            "# The list of given answers is formatted precisely as:",
            "Answer #{index} is:",
            "{answer}",
            "# INSTRUCTIONS: ",
            "# Give a grade from 0.0 to 10.0",
            "# Same answers must have the same grade.",
            "# Irrelevant or empty answer must be graded 0.0",
            "# For each given answer, your grade will be formatted precisely as:",
            "grade #{index}: {grade as float} - short justification",
        ]
        prompt = "\n".join(task_description)
        return prompt

    @staticmethod
    def _build_system_prompt_single_answer() -> str:
        """Build prompt that will be sent to the inner `LLM`."""

        task_description = [
            "# You are a grading expert, grading how accurate and relevant an answer is to a given question.",
            "# INSTRUCTIONS: ",
            "# Give a grade from 0.0 to 10.0",
            "# Irrelevant or empty answer must be graded 0.0",
            "# Your grade will be formatted precisely as:",
            "grade: {grade as float} - short justification",
        ]
        prompt = "\n".join(task_description)
        return prompt
