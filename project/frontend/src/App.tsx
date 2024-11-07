import React, { useEffect, useState } from 'react';
import { Node } from './types';

// Types
interface Node {
    id: string;
    content: string;
    node_type: 'SYSTEM' | 'PROMPT' | 'RESPONSE';
    model_config: Record<string, any>;
    timestamp: string;
    parent_id: string | null;
    has_children: boolean;
    children?: Node[];
}

// API functions
const api = {
    fetchNode: async (nodeId: string): Promise<Node> => {
        const response = await fetch(`http://localhost:8000/api/nodes/${nodeId}`);
        if (!response.ok) throw new Error('Failed to fetch node');
        return response.json();
    },

    fetchRoots: async (): Promise<Node[]> => {
        const response = await fetch('http://localhost:8000/api/roots');
        if (!response.ok) throw new Error('Failed to fetch roots');
        return response.json();
    }
};

// Main component
function App() {
    const [nodes, setNodes] = useState<Node[]>([]);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.fetchRoots()
            .then(setNodes)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div>Loading...</div>;

    return (
        <div className="container mx-auto p-4">
            <div className="flex gap-4">
                {/* Tree View - Ready for visualization enhancement */}
                <div className="w-2/3 border rounded p-4">
                    <h2 className="text-xl mb-4">Conversation Tree</h2>
                    {/* This is where you'll add your visualization */}
                    <pre>{JSON.stringify(nodes, null, 2)}</pre>
                </div>

                {/* Details Panel */}
                <div className="w-1/3 border rounded p-4">
                    <h2 className="text-xl mb-4">Node Details</h2>
                    {selectedNode ? (
                        <div>
                            <h3>{selectedNode.node_type}</h3>
                            <p>{selectedNode.content}</p>
                        </div>
                    ) : (
                        <p>Select a node to view details</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;