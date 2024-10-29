from abc import ABC
from typing import List, Dict, Any

import anthropic
from src.agents.base import Agent, ResponseGenerator
from src.graph.conversation_graph import ConversationGraph, Node

key = ""


class BasicResponseGenerator(ResponseGenerator, ABC):
    def __init__(self):
        model_config = {
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
        }
        system_prompt = ""
        super().__init__(model_config, system_prompt)

    def get_response(self, prompt: str, context: List[Node]) -> str:
        client = anthropic.Anthropic(api_key=key)

        message = client.messages.create(
            model=self.model_config.get("model"),
            max_tokens=1000,
            temperature=self.model_config.get("temperature"),
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        )

        return message.content[0].text



class BasicAgent(Agent, ABC):
    def __init__(self, graph: ConversationGraph, response_generator: ResponseGenerator, system: str):
        self.system = system
        model_config = {
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
        }
        super().__init__(graph, response_generator, model_config)

    def generate_decision(self, choices) -> str:
        client = anthropic.Anthropic(api_key=key)

        prompt = self.create_prompt(choices, self.model_config.get("model"))

        message = client.messages.create(
            model=self.model_config.get("model"),
            max_tokens=1000,
            temperature=self.model_config.get("temperature"),
            system=self.system,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        )
        return message.content[0].text

    def format_conversation_path(self) -> str:
        # Skip the system prompt
        path_nodes = self.context[1:]
        if not path_nodes:
            return "You are at the beginning of the conversation."

        formatted_lines = []

        for node in path_nodes:
            model = node.model_config.get('model', 'unknown')
            formatted_lines.append(
                f"({model}) [{node.node_type.value}]: {node.content}"
            )

        return "\n".join(formatted_lines)

    def create_prompt(self, choices: str, model: str) -> str:
        prompt = \
            f"""You are {model} participating in a multi-ai conversation.
    
The conversation so far:
{self.format_conversation_path()}

Available next paths:
{choices}

You may:
- Follow one of the above paths by responding: <choice>FOLLOW:N</choice>
- Create a new prompt as {model} by responding: <choice>NEW:your prompt</choice>
    """

        return prompt