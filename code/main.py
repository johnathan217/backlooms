from typing import List, Dict, Any

from models import Agent, SimpleResponseGenerator, RandomAgent
from conversationGraph import ConversationGraph, NodeType, Node

if __name__ == "__main__":
    graph = ConversationGraph(
        system_prompt="You are a helpful AI assistant focused on teaching Python programming concepts.",
        model_config={"model": "claude-3", "temperature": 0.7}
    )

    # Create some initial conversation branches
    prompt1 = graph.add_node(
        "Can you explain what a Python list is?",
        NodeType.PROMPT,
        graph.root.id
    )

    response1 = graph.add_node(
        "A Python list is a built-in data structure that can hold multiple items. Lists are ordered, mutable, and can contain items of different types.",
        NodeType.RESPONSE,
        prompt1.id
    )

    # Add some branches from response1
    prompt2a = graph.add_node(
        "Can you show me some examples of list operations?",
        NodeType.PROMPT,
        response1.id
    )

    response2a = graph.add_node(
        "Here are some common list operations:\n1. append(): adds item to end\n2. pop(): removes last item\n3. insert(): adds item at position",
        NodeType.RESPONSE,
        prompt2a.id
    )

    prompt2b = graph.add_node(
        "What's the difference between lists and tuples?",
        NodeType.PROMPT,
        response1.id
    )

    response2b = graph.add_node(
        "The main differences are:\n1. Lists are mutable, tuples are immutable\n2. Lists use square brackets [], tuples use parentheses ()",
        NodeType.RESPONSE,
        prompt2b.id
    )

    try:
        graph.validate_tree()
        print("VALIDATED GRAPH STRUCTURE")
    except ValueError as e:
        print(f"Graph validation failed: {e}")

    response_gen = SimpleResponseGenerator()
    agent = RandomAgent(graph, response_gen)

    print("\nStarting agent journey...")
    agent.start_journey(
        response1.id,
        "Explore and expand knowledge about Python data structures, focusing on practical examples and use cases."
    )

    print("\nCurrent conversation path:")
    for node in agent.context:
        print(f"{node.node_type}: {node.content[:50]}...")

    print("\nAvailable children at current position:")
    children = graph.get_children(agent.current_node_id)
    for child in children:
        print(f"{child.node_type}: {child.content[:50]}...")
