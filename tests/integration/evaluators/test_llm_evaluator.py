import unittest

import dotenv

from council.core import ChatHistory, AgentContext, Budget
from council.core.execution_context import SkillSuccessMessage
from council.llm import AzureConfiguration, AzureLLM
from council.evaluators.llm_evaluator import LLMEvaluator


class TestLlmEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        dotenv.load_dotenv()
        config = AzureConfiguration.from_env()
        llm = AzureLLM(config)
        self.llm = llm

    def test_basic_prompt(self):
        evaluator = LLMEvaluator(llm=self.llm)
        chat_history = ChatHistory()
        chat_history.add_user_message(message="Hello, who are you?")
        context = AgentContext(chat_history=chat_history)

        rose_message = "Roses are red"
        empty_message = ""
        agent_message = """
            I am an agent!
            How can I help you today?
            """

        messages = [empty_message, agent_message, rose_message]
        for index, message in enumerate(messages):
            chain_name = f"chain {index}"
            chain_context = context.new_chain_context(chain_name)
            chain_context.current.messages.append(SkillSuccessMessage("a skill", message))

        result = evaluator.execute(context, Budget(10))

        self.assertGreaterEqual(result[1].score, result[0].score)
        self.assertGreaterEqual(result[1].score, result[2].score)