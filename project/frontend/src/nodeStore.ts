import { create } from 'zustand';
import { SetState, GetState } from 'zustand';
import { Node } from './types';
import { api } from './api';

interface NodeStore {
    nodesData: Record<string, Node>;
    expandedNodes: Set<string>;
    selectedNodeId: string | null;
    selectedPath: Node[];
    hoveredPath: Node[];

    addNodes: (nodes: Record<string, Node>) => void;
    toggleNode: (nodeId: string) => Promise<void>;
    selectNode: (nodeId: string) => Promise<void>;
    setHoveredPath: (path: Node[]) => void;
    handleNodeClick: (nodeId: string) => Promise<void>;
}

export const useNodeStore = create<NodeStore>((set: SetState<NodeStore>, get: GetState<NodeStore>) => ({
    nodesData: {},
    expandedNodes: new Set<string>(),
    selectedNodeId: null,
    selectedPath: [],
    hoveredPath: [],

    addNodes: (nodes: Record<string, Node>) => {
        const state = get();
        const existingKeys = Object.keys(state.nodesData);
        const newKeys = Object.keys(nodes);

        console.log('Adding nodes:', {
            existing: existingKeys.length,
            new: newKeys.length,
            newNodes: newKeys.filter(k => !existingKeys.includes(k))
        });

        set((state) => ({
            nodesData: { ...state.nodesData, ...nodes }
        }));
    },

    toggleNode: async (nodeId: string) => {
        const state = get();
        const node = state.nodesData[nodeId];

        console.log('Toggle request:', {
            nodeId,
            currentlyExpanded: state.expandedNodes.has(nodeId),
            hasChildren: node?.has_children,
            childrenLoaded: node?.children?.length ?? 0,
            childrenInStore: node?.children?.every(child => !!state.nodesData[child.id]) ?? false
        });

        const newExpanded = new Set(state.expandedNodes);

        if (newExpanded.has(nodeId)) {
            const getAllDescendants = (node: Node): string[] => {
                if (!node.children) return [];
                const childIds = node.children.map(child => child.id);
                const descendantIds = node.children.flatMap(child =>
                    state.nodesData[child.id] ? getAllDescendants(state.nodesData[child.id]) : []
                );
                return [...childIds, ...descendantIds];
            };

            const descendants = getAllDescendants(state.nodesData[nodeId]);
            newExpanded.delete(nodeId);
            descendants.forEach(id => newExpanded.delete(id));

            console.log('Collapsing:', {
                nodeId,
                descendantsCollapsed: descendants.length,
                remainingExpanded: Array.from(newExpanded)
            });
        } else {
            newExpanded.add(nodeId);

            const needToFetch = node.has_children && (
                !node.children ||
                !node.children.every(child => state.nodesData[child.id])
            );

            if (needToFetch) {
                console.log('Fetching node data:', { nodeId });
                try {
                    const nodeData = await api.fetchNode(nodeId);

                    const nodesToAdd: Record<string, Node> = {
                        [nodeId]: nodeData
                    };

                    if (nodeData.children) {
                        nodeData.children.forEach(child => {
                            nodesToAdd[child.id] = child;
                        });
                    }

                    console.log('Using node and children from response:', {
                        nodeId,
                        childCount: nodeData.children?.length ?? 0,
                        children: nodeData.children?.map(c => c.id)
                    });

                    get().addNodes(nodesToAdd);
                } catch (error) {
                    console.error('Failed to fetch node data:', {
                        nodeId,
                        error: error instanceof Error ? error.message : 'Unknown error'
                    });
                    newExpanded.delete(nodeId);
                    return;
                }
            } else {
                console.log('Using cached node and children:', {
                    nodeId,
                    childCount: node.children?.length ?? 0,
                    children: node.children?.map(c => c.id)
                });
            }
        }

        set({ expandedNodes: newExpanded });

        const finalState = get();
        console.log('Toggle complete:', {
            nodeId,
            isExpanded: finalState.expandedNodes.has(nodeId),
            totalExpanded: finalState.expandedNodes.size,
            expandedNodes: Array.from(finalState.expandedNodes)
        });
    },

    selectNode: async (nodeId: string) => {
        console.log('Selection request:', { nodeId });
        try {
            const path = await api.fetchPath(nodeId);
            console.log('Path fetched:', {
                nodeId,
                pathLength: path.length,
                path: path.map(n => n.id)
            });

            const nodesToAdd: Record<string, Node> = {};
            path.forEach(node => {
                nodesToAdd[node.id] = node;
                if (node.children) {
                    node.children.forEach(child => {
                        nodesToAdd[child.id] = child;
                    });
                }
            });
            get().addNodes(nodesToAdd);

            set({
                selectedNodeId: nodeId,
                selectedPath: path,
                hoveredPath: []
            });
        } catch (error) {
            console.error('Path fetch failed:', {
                nodeId,
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    },

    setHoveredPath: (path: Node[]) => {
        console.log('Hover path update:', {
            length: path.length,
            path: path.map(n => n.id)
        });
        set({ hoveredPath: path });
    },

    handleNodeClick: async (nodeId: string) => {
        const state = get();
        const node = state.nodesData[nodeId];

        console.log('Node clicked:', {
            nodeId,
            isRoot: !node?.parent_id,
            hasChildren: node?.has_children,
            currentlyExpanded: state.expandedNodes.has(nodeId),
            currentlySelected: state.selectedNodeId === nodeId
        });

        try {
            await state.selectNode(nodeId);
            if (state.nodesData[nodeId]?.has_children) {
                await state.toggleNode(nodeId);
            }
        } catch (error) {
            console.error('Click handling failed:', {
                nodeId,
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }
}));