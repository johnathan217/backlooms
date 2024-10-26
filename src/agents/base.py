import re
import uuid
from abc import ABC, abstractmethod
from random import sample
from typing import Optional, Tuple, List, Dict, Any

from src.agents.agent_logger import setup_agent_logger
from src.graph.conversation_graph import ConversationGraph, Node, NodeType


class ResponseGenerator(ABC):
    @abstractmethod
    def get_response(self, context: List[Node], model_config: Dict[str, Any]) -> str:
        pass


class Agent(ABC):
    def __init__(self, graph: ConversationGraph, response_generator: ResponseGenerator):
        self.id = str(uuid.uuid4())[:8]
        self.logger = setup_agent_logger(self.id)
        self.graph = graph
        self.response_generator = response_generator
        self.current_node_id = None
        self.context = []
        self.max_choices = 5

        self.logger.info("Agent started", extra={
            'data': {
                'agent_id': self.id
            }
        })

    @abstractmethod
    def generate_decision(self, agent_context):
        pass

    def _log_node_reached(self, node: Node):
        self.logger.info("At node", extra={
            'data': {
                'node_type': node.node_type.name,
                'node_id': node.id,
                'content': node.content[:100] + '...' if len(node.content) > 100 else node.content
            }
        })

    def _present_choices(self) -> str:
        children = self.graph.get_children(self.current_node_id)
        prompt_nodes = [n for n in children if n.node_type == NodeType.PROMPT]

        if len(prompt_nodes) > self.max_choices:
            prompt_nodes = sample(prompt_nodes, self.max_choices)

        self.logger.info("Available choices", extra={
            'data': {
                'num_choices': len(prompt_nodes),
                'choices': [{'id': node.id, 'content': node.content[:100]} for node in prompt_nodes]
            }
        })

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

    def start_journey(self, start_node_id: str, instructions: str) -> None:
        node = self.graph.get_node(start_node_id)
        if node.node_type == NodeType.PROMPT:
            raise ValueError("Agent cannot start on a prompt node")

        self.logger.info("Starting journey", extra={
            'data': {
                'start_node': start_node_id,
                'instructions': instructions
            }
        })

        self.current_node_id = start_node_id
        self.context = self.graph.get_conversation_path(start_node_id)
        self._log_node_reached(node)
        self._process_current_position(instructions)

    def _process_agent_decision(self, decision: str) -> Tuple[bool, Optional[str], Optional[str]]:
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

                self.logger.info("Following existing path", extra={
                    'data': {
                        'choice': choice,
                        'prompt_id': chosen_prompt.id,
                        'prompt': chosen_prompt.content,
                        'response_id': response_node.id
                    }
                })

                return (False, response_node.id, None)
            except Exception as e:
                self.logger.info("Error following path", extra={
                    'data': {
                        'error': str(e),
                        'choice': choice
                    }
                })
                raise ValueError("Invalid FOLLOW format in choice")

        elif choice.startswith("NEW:"):
            new_prompt = choice.split(":", 1)[1].strip()
            self.logger.info("Creating new branch", extra={
                'data': {
                    'choice': choice,
                    'prompt': new_prompt
                }
            })
            return (True, new_prompt, None)

        raise ValueError("Invalid choice format")

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
            prompt_id = self.graph.add_node(
                content=result,
                node_type=NodeType.PROMPT,
                parent_id=self.current_node_id
            )
            prompt_node = self.graph.get_node(prompt_id)

            context = self.graph.get_conversation_path(prompt_id)
            root_node = context[0]
            response = self.response_generator.get_response(
                context,
                root_node.model_config
            )

            response_id = self.graph.add_node(
                content=response,
                node_type=NodeType.RESPONSE,
                parent_id=prompt_id
            )
            response_node = self.graph.get_node(response_id)

            self.logger.info("Generated response", extra={
                'data': {
                    'prompt_id': prompt_id,
                    'response_id': response_id,
                    'response': response[:100] + '...' if len(response) > 100 else response
                }
            })

            self.current_node_id = response_id
            self._log_node_reached(response_node)
        else:
            self.current_node_id = result
            node = self.graph.get_node(result)
            self._log_node_reached(node)

        self.context = self.graph.get_conversation_path(self.current_node_id)
        self.logger.info("Updated path", extra={
            'data': {
                'path': [(node.node_type.name, node.id) for node in self.context]
            }
        })

    def __del__(self):
        if hasattr(self, 'logger'):
            self.logger.info("Agent finished", extra={
                'data': {
                    'agent_id': self.id
                }
            })
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
