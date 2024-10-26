from typing import List, Dict, Any
import random
from src.agents.base import Agent, ResponseGenerator
from src.graph.conversation_graph import Node


class RandomAgent(Agent):
    def generate_decision(self, context: str) -> str:
        if random.choice([True, False]):
            return "<choice>NEW: Let's explore a new direction</choice>"
        return "<choice>FOLLOW: 1</choice>"


class SimpleResponseGenerator(ResponseGenerator):
    def get_response(self, context: List[Node], model_config: Dict[str, Any]) -> str:
        return "Simple Response"
