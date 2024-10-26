from sqlalchemy import create_engine, Column, String, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.mysql import ENUM, JSON
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

Base = declarative_base()


class DBNode(Base):
    __tablename__ = 'conversation_nodes'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    content = Column(Text, nullable=False)

    node_type = Column(
        ENUM('SYSTEM', 'PROMPT', 'RESPONSE', name='node_type_enum'),
        nullable=False
    )

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
            'timestamp': self.timestamp.isoformat(),
            'parent_id': self.parent_id
        }


class MySQLConversationGraph:
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

    def create_graph(self, system_prompt: str, model_config: Dict[str, Any]) -> str:
        session = self.Session()
        try:
            root = DBNode(
                content=system_prompt,
                node_type='SYSTEM',
                model_config=model_config
            )
            session.add(root)
            session.commit()
            return root.id
        finally:
            session.close()

    def add_node(self, content: str, node_type: str,
                 parent_id: str,
                 model_config: Optional[Dict[str, Any]] = None) -> str:
        session = self.Session()
        try:
            parent = session.query(DBNode).filter(DBNode.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent node {parent_id} not found")

            node = DBNode(
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

    def get_node(self, node_id: str) -> Optional[Dict]:
        session = self.Session()
        try:
            node = session.query(DBNode).filter(DBNode.id == node_id).first()
            if not node:
                return None

            children = session.query(DBNode.id) \
                .filter(DBNode.parent_id == node_id) \
                .all()

            result = node.to_dict()
            result['children_ids'] = [child[0] for child in children]
            return result
        finally:
            session.close()

    def get_conversation_path(self, node_id: str) -> List[Dict]:
        query = """
        WITH RECURSIVE path_cte AS (
            SELECT id, content, node_type, model_config, timestamp, parent_id, 1 as level
            FROM conversation_nodes
            WHERE id = :node_id

            UNION ALL

            SELECT n.id, n.content, n.node_type, n.model_config, n.timestamp, n.parent_id, p.level + 1
            FROM conversation_nodes n
            INNER JOIN path_cte p ON n.id = p.parent_id
        )
        SELECT * FROM path_cte
        ORDER BY level DESC;
        """

        session = self.Session()
        try:
            result = session.execute(query, {'node_id': node_id})
            path = []
            for row in result:
                path.append({
                    'id': row.id,
                    'content': row.content,
                    'node_type': row.node_type,
                    'model_config': row.model_config,
                    'timestamp': row.timestamp.isoformat(),
                    'parent_id': row.parent_id
                })
            return path
        finally:
            session.close()

    def get_children(self, node_id: str) -> List[Dict]:
        session = self.Session()
        try:
            children = session.query(DBNode) \
                .filter(DBNode.parent_id == node_id) \
                .all()
            return [child.to_dict() for child in children]
        finally:
            session.close()

    def validate_tree(self, root_id: str) -> bool:
        session = self.Session()
        try:
            root = session.query(DBNode).filter(DBNode.id == root_id).first()
            if not root or root.node_type != 'SYSTEM':
                return False

            query = """
            WITH RECURSIVE tree_cte AS (
                SELECT id, node_type, parent_id, 0 as level
                FROM conversation_nodes
                WHERE id = :root_id

                UNION ALL

                SELECT n.id, n.node_type, n.parent_id, t.level + 1
                FROM conversation_nodes n
                INNER JOIN tree_cte t ON n.parent_id = t.id
            )
            SELECT t1.id, t1.node_type, t1.level,
                   t2.node_type as parent_type
            FROM tree_cte t1
            LEFT JOIN tree_cte t2 ON t1.parent_id = t2.id
            ORDER BY t1.level;
            """

            result = session.execute(query, {'root_id': root_id})

            valid_transitions = {
                None: {'SYSTEM'},
                'SYSTEM': {'PROMPT'},
                'PROMPT': {'RESPONSE'},
                'RESPONSE': {'PROMPT'}
            }

            for row in result:
                if row.parent_type not in valid_transitions or \
                        row.node_type not in valid_transitions[row.parent_type]:
                    return False

            return True
        finally:
            session.close()