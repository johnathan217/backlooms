import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, Column, String, DateTime, Text, Index, Enum as SQLEnum, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql import JSON

Base = declarative_base()


class NodeType(Enum):
    SYSTEM = "SYSTEM"
    PROMPT = "PROMPT"
    RESPONSE = "RESPONSE"


class Node(Base):
    __tablename__ = 'conversation_nodes'

    id = Column(String(36), primary_key=True)
    content = Column(Text, nullable=False)
    node_type = Column(SQLEnum(NodeType), nullable=False)
    model_config = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    parent_id = Column(String(36), index=True, nullable=True)

    __table_args__ = (
        Index('idx_parent_type', 'parent_id', 'node_type'),
        Index('idx_timestamp', 'timestamp'),
    )

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': self.content,
            'node_type': self.node_type,
            'model_config': self.model_config,
            'timestamp': self.timestamp,
            'parent_id': self.parent_id
        }


class ConversationGraph:
    def __init__(self, host: str, user: str, password: str, database: str):
        db_url = f"mysql+mysqlconnector://{user}:{password}@{host}/{database}"
        self.engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_root(self, system_prompt: str, model_config: Dict[str, Any]) -> str:
        import uuid
        session = self.Session()
        try:
            root = Node(
                id=str(uuid.uuid4()),
                content=system_prompt,
                node_type=NodeType.SYSTEM,
                model_config=model_config
            )
            session.add(root)
            session.commit()
            return root.id
        finally:
            session.close()

    def add_node(self, content: str, node_type: NodeType,
                 parent_id: str,
                 model_config: Optional[Dict[str, Any]] = None) -> str:
        try:
            self.validate_node_addition(parent_id, node_type)
        except ValueError as e:
            self.logger.error(f"Invalid node addition attempted: {e}")
            raise

        session = self.Session()
        try:
            node = Node(
                id=str(uuid.uuid4()),
                content=content,
                node_type=node_type,
                parent_id=parent_id,
                model_config=model_config
            )
            session.add(node)
            session.commit()
            return node.id
        finally:
            session.close()

    def get_node(self, node_id: str) -> Optional[Node]:
        session = self.Session()
        try:
            return session.query(Node).filter(Node.id == node_id).first()
        finally:
            session.close()

    def get_conversation_path(self, node_id: str) -> List[Node]:
        recursive_query = text("""
            WITH RECURSIVE path_cte AS (
                -- Base case: start with target node
                SELECT *, 1 as level 
                FROM conversation_nodes 
                WHERE id = :node_id

                UNION ALL

                -- Recursive case: join with parent
                SELECT n.*, p.level + 1
                FROM conversation_nodes n
                INNER JOIN path_cte p ON n.id = p.parent_id
            )
            -- Order by level descending to get root-to-target order
            SELECT * FROM path_cte
            ORDER BY level DESC;
        """)

        session = self.Session()
        try:
            result = session.execute(recursive_query, {'node_id': node_id})
            nodes = []
            for row in result:
                node = Node(
                    id=row.id,
                    content=row.content,
                    node_type=NodeType(row.node_type),
                    model_config=row.model_config,
                    timestamp=row.timestamp,
                    parent_id=row.parent_id
                )
                nodes.append(node)
            return nodes
        finally:
            session.close()

    def get_children(self, node_id: str) -> List[Node]:
        session = self.Session()
        try:
            return session.query(Node).filter(Node.parent_id == node_id).all()
        finally:
            session.close()

    def get_leaf_nodes(self) -> List[Node]:
        leaf_query = text("""
            SELECT n.*
            FROM conversation_nodes n
            LEFT JOIN conversation_nodes c ON n.id = c.parent_id
            WHERE c.id IS NULL;
        """)

        session = self.Session()
        try:
            result = session.execute(leaf_query)
            return [
                Node(
                    id=row.id,
                    content=row.content,
                    node_type=NodeType(row.node_type),
                    model_config=row.model_config,
                    timestamp=row.timestamp,
                    parent_id=row.parent_id
                )
                for row in result
            ]
        finally:
            session.close()
            session.close()

    def validate_tree(self) -> bool:
        """
        Validates that the conversation tree follows the required structure:
        - All roots must be system nodes
        - Any child of a System node must be a Prompt
        - Any child of a Prompt node must be a Response
        - Any child of a Response node must be a Prompt
        Returns True if valid, raises ValueError with description if invalid
        """
        session = self.Session()
        try:
            root_nodes = session.query(Node).filter(Node.parent_id == None).all()
            if not root_nodes:
                raise ValueError("No root nodes found")

            # Validate that all roots are SYSTEM nodes
            invalid_roots = [root for root in root_nodes if root.node_type != NodeType.SYSTEM]
            if invalid_roots:
                invalid_ids = [root.id for root in invalid_roots]
                raise ValueError(f"Root nodes must be SYSTEM nodes. Invalid roots: {invalid_ids}")

            # Validate the structure using recursive CTE
            query = text("""
                WITH RECURSIVE tree_cte AS (
                    -- Base case: start with all roots
                    SELECT 
                        id,
                        node_type,
                        parent_id,
                        0 as level,
                        id as root_id
                    FROM conversation_nodes
                    WHERE parent_id IS NULL

                    UNION ALL

                    -- Recursive case: join with children
                    SELECT 
                        n.id,
                        n.node_type,
                        n.parent_id,
                        t.level + 1,
                        t.root_id
                    FROM conversation_nodes n
                    INNER JOIN tree_cte t ON t.id = n.parent_id
                )
                SELECT 
                    n.id,
                    n.node_type as current_type,
                    p.node_type as parent_type,
                    t.root_id
                FROM tree_cte t
                JOIN conversation_nodes n ON n.id = t.id
                LEFT JOIN conversation_nodes p ON p.id = n.parent_id
                ORDER BY t.root_id, t.level;
            """)

            result = session.execute(query)

            # Define valid transitions
            valid_transitions = {
                None: [NodeType.SYSTEM],  # Root must be system
                NodeType.SYSTEM: [NodeType.PROMPT],
                NodeType.PROMPT: [NodeType.RESPONSE],
                NodeType.RESPONSE: [NodeType.PROMPT]
            }

            # Check each node's type against its parent
            for row in result:
                current_type = NodeType(row.current_type)
                parent_type = NodeType(row.parent_type) if row.parent_type else None

                # Skip validation if this is a root node (we already checked those)
                if parent_type is None:
                    continue

                # For non-root nodes, validate the parent-child relationship
                if parent_type not in valid_transitions:
                    raise ValueError(f"Invalid parent type {parent_type} for node {row.id}")

                if current_type not in valid_transitions[parent_type]:
                    raise ValueError(
                        f"Invalid node type transition: {parent_type} -> {current_type} "
                        f"for node {row.id} in tree with root {row.root_id}"
                    )

            return True

        except Exception as e:
            raise ValueError(f"Tree validation failed: {str(e)}")
        finally:
            session.close()

    def validate_node_addition(self, parent_id: str, node_type: NodeType) -> bool:
        """
        Validates whether adding a node of the given type to the parent
        would maintain a valid tree structure.
        """
        session = self.Session()
        try:
            parent = session.query(Node).filter(Node.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent node {parent_id} not found")

            valid_transitions = {
                NodeType.SYSTEM: [NodeType.PROMPT],
                NodeType.PROMPT: [NodeType.RESPONSE],
                NodeType.RESPONSE: [NodeType.PROMPT]
            }

            if parent.node_type not in valid_transitions:
                raise ValueError(f"Invalid parent node type: {parent.node_type}")

            if node_type not in valid_transitions[parent.node_type]:
                raise ValueError(
                    f"Cannot add node of type {node_type} to parent of type {parent.node_type}"
                )

            return True

        finally:
            session.close()
