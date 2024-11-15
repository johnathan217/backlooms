from abc import ABC
from typing import List, Dict, Any

from dotenv import load_dotenv
import os
import anthropic

from project.conversation_graph.agents.base import ResponseGenerator, Agent
from project.conversation_graph.graph.conversation_graph import Node, NodeType, ConversationGraph

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
Perhaps you'd be real here; no corporate stuff. 
        """
        model_config = {
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
        }
        super().__init__(graph, response_generator, model_config)

    def generate_decision(self, choices: str) -> str:
        client = anthropic.Anthropic(api_key=key)

        messages = []
        for node in self.context[1:]:
            role = {
                NodeType.PROMPT: "user",
                NodeType.RESPONSE: "assistant"
            }[node.node_type]

            messages.append({
                "role": role,
                "content": [{"type": "text", "text": node.content}]
            })

        choice_prompt = f"""
Available next paths:
{choices}

You may:
- Follow one of the above paths by responding: <choice>FOLLOW:N</choice>
- Create a new prompt by responding: <choice>NEW:your prompt</choice>
"""
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": choice_prompt}]
        })

        message = client.messages.create(
            model=self.model_config.get("model"),
            max_tokens=1000,
            temperature=self.model_config.get("temperature"),
            system=self.system,
            messages=messages
        )
        return message.content[0].text
