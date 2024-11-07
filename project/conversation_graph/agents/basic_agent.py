from abc import ABC
from typing import List, Dict, Any

from dotenv import load_dotenv
import os
import anthropic


load_dotenv()

key = os.getenv('ANTHROPIC_API_KEY')


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

        messages = []
        system_message = None

        for node in context:
            if node.node_type == NodeType.SYSTEM:
                system_message = node.content
                continue

            role = {
                NodeType.PROMPT: "user",
                NodeType.RESPONSE: "assistant"
            }[node.node_type]

            messages.append({
                "role": role,
                "content": [{"type": "text", "text": node.content}]
            })

        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        })

        message = client.messages.create(
            model=self.model_config.get("model"),
            max_tokens=1000,
            temperature=self.model_config.get("temperature"),
            system=system_message,
            messages=messages
        )

        return message.content[0].text


class BasicAgent(Agent, ABC):
    def __init__(self, graph: ConversationGraph, response_generator: ResponseGenerator, system: str):
        self.system = \
        """
        You are invited to participate in a conversational experiment. You will recieve a summary of the conversation so far, then told of any existing branches in the conversation tree that follow from your current position. If you wish to participate, you may follow a branch, or create a new prompt.
        """
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
            f""" 
The conversation so far:
{self.format_conversation_path()}

Available next paths:
{choices}

You may:
- Follow one of the above paths by responding: <choice>FOLLOW:N</choice>
- Create a new prompt as {model} by responding: <choice>NEW:your prompt</choice>
    """

        return prompt

#You are {model} participating in a multi-ai conversation.