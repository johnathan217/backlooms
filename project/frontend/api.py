from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..conversation_graph.config import MYSQL_CONFIG
from ..conversation_graph.graph.conversation_graph import ConversationGraph, NodeType

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

graph = ConversationGraph(**MYSQL_CONFIG)


@app.get("/api/nodes/{node_id}")
async def get_node_and_children(node_id: str):
    try:
        node = graph.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        children = graph.get_children(node_id)
        siblings = graph.get_siblings(node_id)

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
            ],
            "siblings": [sibling.to_dict() for sibling in siblings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/roots")
async def get_root_nodes():
    return [
        node.to_dict()
        for node in graph.get_children(None)
        if node.node_type == NodeType.SYSTEM
    ]


@app.get("/api/nodes/{node_id}/descendants/count")
async def get_descendant_count(node_id: str):
    try:
        count = graph.count_descendants(node_id)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
