from abc import ABC, abstractmethod
from random import sample
from typing import Optional, Tuple, List, Dict, Any
import re

from src.graph.conversation_graph import ConversationGraph, Node, NodeType


class ResponseGenerator(ABC):
    @abstractmethod
    def get_response(self, context: List[Node], model_config: Dict[str, Any]) -> str:
        pass


class Agent(ABC):
    def __init__(self, graph: ConversationGraph, response_generator: ResponseGenerator):
        self.graph = graph
        self.response_generator = response_generator
        self.current_node_id = None
        self.context = []
        self.max_choices = 5

    @abstractmethod
    def generate_decision(self, context: str) -> str:
        """Generate agent's decision - must be implemented by subclasses"""
        pass

    def start_journey(self, start_node_id: str, instructions: str) -> None:
        node = self.graph.get_node(start_node_id)
        if node.node_type == NodeType.PROMPT:
            raise ValueError("Agent cannot start on a prompt node")

        self.current_node_id = start_node_id
        self.context = self.graph.get_conversation_path(start_node_id)
        self._process_current_position(instructions)

    def _process_agent_decision(self, decision: str) -> Tuple[bool, Optional[str], Optional[str]]:
        # returns (is_new_path, node_id/prompt, None)

        choice_match = re.search(r'<choice>(.*?)</choice>', decision, re.DOTALL)
        if not choice_match:
            raise ValueError("No <choice> tags found in decision")

        choice = choice_match.group(1).strip()

        if choice.startswith("FOLLOW:"):
            try:
                path_num = int(choice.split(":")[1].strip())
                children = self.graph.get_children(self.current_node_id)
                prompt_nodes = [n for n in children if n.node_type == NodeType.PROMPT]
                if len(prompt_nodes) > self.max_choices:
                    prompt_nodes = sample(prompt_nodes, self.max_choices)
                chosen_prompt = prompt_nodes[path_num - 1]
                response_node = self.graph.get_children(chosen_prompt.id)[0]
                return (False, response_node.id, None)
            except:
                raise ValueError("Invalid FOLLOW format in choice")

        elif choice.startswith("NEW:"):
            new_prompt = choice.split(":", 1)[1].strip()
            return (True, new_prompt, None)

        raise ValueError("Invalid choice format")

    def _present_choices(self) -> str:
        children = self.graph.get_children(self.current_node_id)
        prompt_nodes = [n for n in children if n.node_type == NodeType.PROMPT]

        if len(prompt_nodes) > self.max_choices:
            prompt_nodes = sample(prompt_nodes, self.max_choices)

        choices_text = "Available paths:\n"
        for idx, node in enumerate(prompt_nodes, 1):
            response = self.graph.get_children(node.id)[0]
            choices_text += f"Path {idx}:\n"
            choices_text += f"Prompt: {node.content}\n"
            choices_text += f"Response: {response.content}\n\n"

        choices_text += "\nTo follow a path, respond with your choice in tags like this:"
        choices_text += "\n<choice>FOLLOW: <path number></choice>"
        choices_text += "\n\nTo create a new path, respond with:"
        choices_text += "\n<choice>NEW: <your prompt></choice>"
        choices_text += "\n\nYou may include any additional explanation or reasoning outside the choice tags."

        return choices_text

    def _process_current_position(self, instructions: str) -> None:
        choices = self._present_choices()

        agent_context = (
            f"Current context: {[node.content for node in self.context]}\n"
            f"Instructions: {instructions}\n"
            f"{choices}"
        )
        decision = self.generate_decision(agent_context)

        is_new_path, result, _ = self._process_agent_decision(decision)

        if is_new_path:
            prompt_node = self.graph.add_node(
                content=result,
                node_type=NodeType.PROMPT,
                parent_id=self.current_node_id
            )

            context = self.graph.get_conversation_path(prompt_node.id)
            response = self.response_generator.get_response(
                context,
                self.graph.root.model_config
            )

            response_node = self.graph.add_node(
                content=response,
                node_type=NodeType.RESPONSE,
                parent_id=prompt_node.id
            )

            self.current_node_id = response_node.id

        else:
            self.current_node_id = result

        self.context = self.graph.get_conversation_path(self.current_node_id)
