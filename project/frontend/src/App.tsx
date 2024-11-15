import React, { useEffect } from 'react';
import { HyperbolicTree } from './components/HyperbolicTree';
import { ConversationPanel } from './components/ConversationPanel';
import { useNodeStore } from './nodeStore';
import { api } from './api';

export function App() {
    const { addNodes, selectNode, selectedPath, hoveredPath } = useNodeStore();

    useEffect(() => {
        const initializeApp = async () => {
            try {
                const roots = await api.fetchRoots();
                if (roots.length > 0) {
                    const rootData = await api.fetchNode(roots[0].id);
                    addNodes({ [rootData.id]: rootData });
                    await selectNode(rootData.id);
                }
            } catch (error) {
                console.error('Failed to initialize app:', error);
            }
        };

        initializeApp();
    }, []);

    return (
        <div className="flex h-screen overflow-hidden">
            <div className="w-2/3 h-full p-4 flex items-center justify-center bg-gray-50">
                <HyperbolicTree />
            </div>
            <div className="w-1/3 h-screen flex flex-col border-l border-gray-200">
                <div className="p-4 border-b border-gray-200 bg-white">
                    <h2 className="text-xl font-bold">Conversation Path</h2>
                </div>
                <div className="flex-1 overflow-y-auto">
                    <ConversationPanel
                        path={hoveredPath.length > 0 ? hoveredPath : selectedPath}
                    />
                </div>
            </div>
        </div>
    );
}

export default App;