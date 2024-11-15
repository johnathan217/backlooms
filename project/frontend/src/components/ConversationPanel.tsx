import React, { useEffect, useRef } from 'react';
import { useNodeStore } from '../nodeStore';
import { Node } from '../types';

interface ConversationPanelProps {
    path: Node[];
}

export const ConversationPanel: React.FC<ConversationPanelProps> = ({ path }) => {
    const { nodesData, selectNode, expandedNodes, toggleNode } = useNodeStore();
    const selectedNodeRef = useRef<HTMLDivElement>(null);

    const handleKeyDown = async (event: KeyboardEvent) => {
        const currentNode = path[path.length - 1];
        if (!currentNode) return;

        switch (event.key) {
            case 'ArrowUp': {
                if (currentNode.parent_id) {
                    await selectNode(currentNode.parent_id);
                }
                break;
            }
            case 'ArrowDown': {
                const currentNodeData = nodesData[currentNode.id];
                if (currentNodeData?.has_children) {
                    if (!expandedNodes.has(currentNode.id)) {
                        await toggleNode(currentNode.id);
                    }

                    const updatedNodeData = nodesData[currentNode.id];
                    if (updatedNodeData?.children && updatedNodeData.children.length > 0) {
                        await selectNode(updatedNodeData.children[0].id);
                    }
                }
                break;
            }
            case 'ArrowLeft':
            case 'ArrowRight': {
                const parentNode = currentNode.parent_id ? nodesData[currentNode.parent_id] : null;
                if (!parentNode?.children || parentNode.children.length <= 1) return;

                const siblings = parentNode.children;
                const currentIndex = siblings.findIndex(node => node.id === currentNode.id);
                if (currentIndex === -1) return;

                const newIndex = event.key === 'ArrowLeft'
                    ? (currentIndex - 1 + siblings.length) % siblings.length
                    : (currentIndex + 1) % siblings.length;

                await selectNode(siblings[newIndex].id);
                break;
            }
        }
    };

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [path, nodesData, expandedNodes]);

    // Add effect to handle scrolling when path changes
    useEffect(() => {
        if (selectedNodeRef.current) {
            selectedNodeRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }, [path]);

    const getNodeColor = (nodeType: Node['node_type']) => {
        switch (nodeType) {
            case 'SYSTEM':
                return 'bg-red-100 border-red-300';
            case 'PROMPT':
                return 'bg-blue-100 border-blue-300';
            case 'RESPONSE':
                return 'bg-green-100 border-green-300';
            default:
                return 'bg-gray-100 border-gray-300';
        }
    };

    const formatTimestamp = (timestamp: string) => {
        return new Date(timestamp).toLocaleString();
    };

    const getNavigationHints = (node: Node) => {
        const hints = [];
        const nodeData = nodesData[node.id];

        if (node.parent_id) {
            hints.push('↑ Parent');
        }

        if (nodeData?.children && nodeData.children.length > 0) {
            hints.push('↓ Child');
        }

        const parentNode = node.parent_id ? nodesData[node.parent_id] : null;
        if (parentNode?.children && parentNode.children.length > 1) {
            hints.push('← → Siblings');
        }

        return hints;
    };

    return (
        <div className="p-4 space-y-4">
            {path.map((node, index) => {
                const isCurrentNode = index === path.length - 1;
                return (
                    <div
                        key={node.id}
                        ref={isCurrentNode ? selectedNodeRef : null}
                        className={`p-4 rounded-lg border ${getNodeColor(node.node_type)} relative 
                            ${isCurrentNode ? 'ring-2 ring-offset-2 ring-blue-500' : ''}`}
                    >
                        {index > 0 && (
                            <div className="absolute -top-3 left-8 w-0.5 h-3 bg-gray-300" />
                        )}
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-semibold text-gray-600">
                                {node.node_type}
                            </span>
                            <span className="text-xs text-gray-500">
                                {formatTimestamp(node.timestamp)}
                            </span>
                        </div>
                        <div className="whitespace-pre-wrap text-gray-800">
                            {node.content}
                        </div>
                        {node.model_config?.model && (
                            <div className="mt-2 text-xs text-gray-500">
                                Model: {node.model_config.model}
                            </div>
                        )}
                        {isCurrentNode && (
                            <>
                                {getNavigationHints(node).length > 0 && (
                                    <div className="mt-2 flex gap-2 flex-wrap">
                                        {getNavigationHints(node).map((hint, index) => (
                                            <span
                                                key={index}
                                                className="text-xs px-2 py-1 bg-gray-200 rounded-full text-gray-700"
                                            >
                                                {hint}
                                            </span>
                                        ))}
                                    </div>
                                )}
                                {nodesData[node.id]?.has_children && (
                                    <div className="mt-2 text-xs text-gray-500">
                                        Has child nodes ({nodesData[node.id]?.children?.length || '?'})
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                );
            })}
        </div>
    );
};