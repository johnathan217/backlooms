import { Node } from './types';

export const fetchNode = async (nodeId: string): Promise<Node> => {
    const response = await fetch(`http://localhost:8000/api/nodes/${nodeId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch node');
    }
    return response.json();
};

export const fetchRoots = async (): Promise<Node[]> => {
    const response = await fetch('http://localhost:8000/api/roots');
    if (!response.ok) {
        throw new Error('Failed to fetch roots');
    }
    return response.json();
};