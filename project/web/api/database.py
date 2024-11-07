from project.conversation_graph.config import MYSQL_CONFIG
from project.conversation_graph.graph.conversation_graph import ConversationGraph


class GraphManager:
    def __init__(self):
        self.graph = ConversationGraph(**MYSQL_CONFIG)


graph_manager = GraphManager()


def get_graph() -> ConversationGraph:
    return graph_manager.graph
