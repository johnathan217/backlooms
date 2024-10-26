from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Protocol
from datetime import datetime
import uuid
from enum import Enum, auto


class NodeType(Enum):
    SYSTEM = auto()
    PROMPT = auto()
    RESPONSE = auto()


@dataclass
class Node:
    content: str
    node_type: NodeType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_config: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)


class ConversationGraph:
    def __init__(self, system_prompt: str, model_config: Dict[str, Any]):
        self.root = Node(
            content=system_prompt,
            node_type=NodeType.SYSTEM,
            model_config=model_config
        )
        self.nodes = {self.root.id: self.root}

    def add_node(self, content: str, node_type: NodeType,
                 parent_id: str,
                 model_config: Optional[Dict[str, Any]] = None) -> Node:

        if not isinstance(node_type, NodeType):
            raise ValueError(f"node_type must be NodeType enum, got {type(node_type)}")
        if parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} not found")

        node = Node(
            content=content,
            node_type=node_type,
            parent_id=parent_id,
            model_config=model_config
        )
        self.nodes[node.id] = node
        self.nodes[parent_id].children_ids.append(node.id)
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def get_conversation_path(self, node_id: str) -> List[Node]:
        """Get the ordered list of nodes from root to target node"""
        path = []
        current = self.nodes.get(node_id)
        while current is not None:
            path.append(current)
            current = self.nodes.get(current.parent_id)
        return list(reversed(path))

    def get_children(self, node_id: str) -> List[Node]:
        """Get all immediate children of a node"""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children_ids]

    def validate_tree(self) -> bool:
        """
        Validates that the conversation tree follows the required structure:
        - Root must be system
        - System must have prompt children
        - Prompt nodes must have response children
        - Response nodes must have prompt children
        Raises ValueError with description of first violation found
        """

        if self.root.node_type != NodeType.SYSTEM:
            raise ValueError("Root node must be a system node")

        def validate_node(node: Node, expected_child_type: NodeType) -> None:
            """Recursively validate node and its children"""
            children = self.get_children(node.id)

            # Skip validation of children if leaf node
            if not children:
                return

            for child in children:
                if child.node_type != expected_child_type:
                    raise ValueError(
                        f"Node {node.id} of type {node.node_type} has child {child.id} "
                        f"of type {child.node_type}, expected {expected_child_type}"
                    )

                # Recursively validate children with their expected child type
                next_expected_type = {
                    NodeType.SYSTEM: NodeType.PROMPT,
                    NodeType.PROMPT: NodeType.RESPONSE,
                    NodeType.RESPONSE: NodeType.PROMPT
                }[child.node_type]

                validate_node(child, next_expected_type)

        # Start validation from root
        validate_node(self.root, NodeType.PROMPT)
        return True
