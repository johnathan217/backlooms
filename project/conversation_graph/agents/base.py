import re
import uuid
from abc import ABC, abstractmethod
from random import sample
from typing import Optional, Tuple, List, Dict, Any

from project.conversation_graph.agents.agent_logger import setup_agent_logger
from project.conversation_graph.graph.conversation_graph import ConversationGraph, Node, NodeType


class ResponseGenerator(ABC):
    def __init__(self, model_config: Dict[str, Any], system_prompt: str):
        self.model_config = model_config
        self.system_prompt = system_prompt

    @abstractmethod
    def get_response(self, prompt: str, context: List[Node]) -> str:
        pass


class Agent(ABC):
    def __init__(self, graph: ConversationGraph, response_generator: ResponseGenerator, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.id = str(uuid.uuid4())[:8]
        self.logger = setup_agent_logger(self.id)
        self.graph = graph
        self.response_generator = response_generator
        self.current_node_id = None
        self.current_prompt_choices = []
        self.max_choices = 5

        self.logger.info("Agent started", extra={
            'data': {
                'agent_id': self.id
            }
        })

    @property
    def context(self) -> List[Node]:
        if self.current_node_id is None:
            return []
        return self.graph.get_conversation_path(self.current_node_id)

    @abstractmethod
    def generate_decision(self, choices) -> str:
        pass

    def hop(self, start_node_id: str) -> str:
        # Should travel one hop from start_node to a response node

        self.graph.validate_tree()

        node = self.graph.get_node(start_node_id)
        if node.node_type == NodeType.PROMPT:
            raise ValueError("Agent cannot start on a prompt node")

        self.logger.info("==================== HOP ====================")
        self.logger.info("At node", extra={
            'data': {
                'node_type': node.node_type.name,
                'id': node.id,
                'content': node.content
            }
        })

        self.current_node_id = start_node_id

        self._process_current_position()

        return self.current_node_id

    def _present_choices(self) -> str:
        children = self.graph.get_children(self.current_node_id)
        prompt_nodes = [n for n in children if n.node_type == NodeType.PROMPT]

        if len(prompt_nodes) > self.max_choices:
            prompt_nodes = sample(prompt_nodes, self.max_choices)

        self.current_prompt_choices = prompt_nodes

        self.logger.info("Available choices", extra={
            'data': {
                'num_choices': len(prompt_nodes),
                'choices': [{'id': node.id, 'content': node.content[:100]} for node in prompt_nodes]
            }
        })

        choices_text = ""
        for idx, node in enumerate(prompt_nodes, 1):
            # response = self.graph.get_children(node.id)[0]
            choices_text += f"Path {idx}:\n"
            choices_text += f"Content: {node.content}\n"
            # choices_text += f"Response: {response.content}\n\n"

        return choices_text

    def _process_agent_decision(self, decision: str) -> Tuple[bool, Optional[str], Optional[str]]:
        choice_match = re.search(r'<choice>(.*?)</choice>', decision, re.DOTALL)
        if not choice_match:
            raise ValueError("No <choice> tags found in decision")

        choice = choice_match.group(1).strip()

        if choice.startswith("FOLLOW:"):
            try:
                path_num = int(choice.split(":")[1].strip())
                chosen_prompt = self.current_prompt_choices[path_num - 1]
                response_node = self.graph.get_children(chosen_prompt.id)[0]

                self.logger.info("Following existing path", extra={
                    'data': {
                        'choice': choice,
                        'id': chosen_prompt.id,
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

    def _process_current_position(self) -> None:

        choices = self._present_choices()

        output = self.generate_decision(choices)

        self.logger.info("AI output", extra={
            'data': {
                'content': output,
            }
        })

        is_new_path, result, _ = self._process_agent_decision(output)

        if is_new_path:
            prompt_id = self.graph.add_node(
                content=result,
                node_type=NodeType.PROMPT,
                parent_id=self.current_node_id,
                model_config=self.model_config
            )

            response = self.response_generator.get_response(
                result,
                self.context
            )

            response_id = self.graph.add_node(
                content=response,
                node_type=NodeType.RESPONSE,
                parent_id=prompt_id,
                model_config=self.response_generator.model_config
            )

            self.current_node_id = response_id

        else:
            self.current_node_id = result

    def __del__(self):
        if hasattr(self, 'logger'):
            self.logger.info("Agent finished", extra={
                'data': {
                    'agent_id': self.id,
                    'path': [(node.node_type.name, node.id) for node in self.context]
                }
            })
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
