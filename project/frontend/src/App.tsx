import React, { useEffect, useState } from 'react';
import HyperbolicTree from './components/HyperbolicTree';

interface Node {
    id: string;
    content: string;
    node_type: 'SYSTEM' | 'PROMPT' | 'RESPONSE';
    model_config: Record<string, any>;
    timestamp: string;
    parent_id: string | null;
    has_children: boolean;
    children?: Node[] | null;
}

function App() {
    const [rootNode, setRootNode] = useState<Node | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchRoot = async () => {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:8000/api/roots');
                if (!response.ok) throw new Error('Failed to fetch roots');
                const roots = await response.json();

                if (roots.length > 0) {
                    const nodeResponse = await fetch(`http://localhost:8000/api/nodes/${roots[0].id}`);
                    if (!nodeResponse.ok) throw new Error('Failed to fetch root node');
                    const nodeData = await nodeResponse.json();
                    setRootNode(nodeData);
                } else {
                    setError('No root nodes found');
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'An error occurred');
            } finally {
                setLoading(false);
            }
        };

        fetchRoot();
    }, []);

    if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>;
    if (!rootNode) return <div className="min-h-screen flex items-center justify-center">No data available</div>;

    return (
        <div className="min-h-screen p-4">
            <HyperbolicTree rootNode={rootNode} />
        </div>
    );
}

export default App;