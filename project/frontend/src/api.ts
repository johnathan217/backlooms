export const api = {
    async fetchNode(nodeId: string) {
        const response = await fetch(`http://localhost:8000/api/nodes/${nodeId}`);
        if (!response.ok) throw new Error('Failed to fetch node');
        return response.json();
    },

    async fetchRoots() {
        const response = await fetch('http://localhost:8000/api/roots');
        if (!response.ok) throw new Error('Failed to fetch roots');
        return response.json();
    },

    async fetchPath(nodeId: string) {
        const path = [];
        let currentNode = await this.fetchNode(nodeId);
        path.unshift(currentNode);

        while (currentNode.parent_id) {
            currentNode = await this.fetchNode(currentNode.parent_id);
            path.unshift(currentNode);
        }

        return path;
    },

    async fetchDescendantCount(nodeId: string): Promise<number> {
        const response = await fetch(`http://localhost:8000/api/nodes/${nodeId}/descendants/count`);
        if (!response.ok) throw new Error('Failed to fetch descendant count');
        const data = await response.json();
        return data.count;
    }
};