from project.conversation_graph.agents.basic_agent import BasicAgent, BasicResponseGenerator
from project.conversation_graph.config import MYSQL_CONFIG
from project.conversation_graph.graph.conversation_graph import ConversationGraph


def main():
    graph = ConversationGraph(**MYSQL_CONFIG)
    graph.validate_tree()

    # cfg = {
    #     "model": "claude-3-sonnet",
    #     "temperature": 0.7,
    #     "max_tokens": 1000,
    # }
    #
    # id = graph.create_root("You are Claude", cfg)

    id = "325a3db7-41d7-4f61-bab8-ddb9643bff12"

    agent = BasicAgent(graph, BasicResponseGenerator(), "system")

    for i in range(0, 7):
        id = agent.hop(id)

    path = graph.get_conversation_path(id)
    print("\nConversation path:")
    for node in path:
        print(f"{node.node_type.value}: {node.content[:100]}...")


if __name__ == "__main__":
    main()
