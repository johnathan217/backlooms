from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from project.conversation_graph.graph.conversation_graph import ConversationGraph, NodeType
from project.web.api.database import get_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/nodes/{node_id}")
async def get_node_and_children(
        node_id: str,
        graph: ConversationGraph = Depends(get_graph)
):
    try:
        node = graph.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        children = graph.get_children(node_id)

        return {
            **node.to_dict(),
            "has_children": len(children) > 0,
            "children": [
                {
                    **child.to_dict(),
                    "has_children": len(graph.get_children(child.id)) > 0,
                    "children": None
                }
                for child in children
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/roots")
async def get_root_nodes(
    graph: ConversationGraph = Depends(get_graph)
):

    nodes = graph.get_children(None)
    return [
        node.to_dict()
        for node in nodes
        if node.node_type == NodeType.SYSTEM
    ]