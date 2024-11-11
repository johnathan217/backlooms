import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

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

interface HyperbolicTreeProps {
    rootNode: Node;
}

const HyperbolicTree: React.FC<HyperbolicTreeProps> = ({ rootNode }) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
    const currentTransformRef = useRef(d3.zoomIdentity);
    const [nodesData, setNodesData] = useState<Record<string, Node>>({});

    const getAllDescendantIds = (nodeId: string, nodes: Record<string, Node>): string[] => {
        const node = nodes[nodeId];
        if (!node?.children) return [];

        const childIds = node.children.map(child => child.id);
        const descendantIds = childIds.flatMap(childId => getAllDescendantIds(childId, nodes));
        return [...childIds, ...descendantIds];
    };

    const fetchNode = async (nodeId: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/nodes/${nodeId}`);
            if (!response.ok) throw new Error('Failed to fetch node');
            const data = await response.json();
            console.log('Fetched data for node:', nodeId, data);

            const newNodes: Record<string, Node> = { [nodeId]: data };
            if (data.children) {
                data.children.forEach((child: Node) => {
                    newNodes[child.id] = child;
                });
            }

            setNodesData(prev => ({...prev, ...newNodes}));
            return data;
        } catch (error) {
            console.error('Error fetching node:', error);
            throw error;
        }
    };

    const nodeColors: Record<Node['node_type'], string> = {
        'SYSTEM': '#ff4444',
        'PROMPT': '#4444ff',
        'RESPONSE': '#44ff44'
    };

    useEffect(() => {
        const initialNodes: Record<string, Node> = { [rootNode.id]: rootNode };
        if (rootNode.children) {
            rootNode.children.forEach(child => {
                initialNodes[child.id] = child;
            });
        }
        setNodesData(initialNodes);
    }, [rootNode]);

    useEffect(() => {
        if (!svgRef.current) return;

        const width = 800;
        const height = 600;
        const centerX = width / 2;
        const centerY = height / 2;

        const processData = (nodeId: string) => {
            const node = nodesData[nodeId];
            if (!node) return null;

            const result: any = {
                name: node.id,
                nodeData: node,
                children: []
            };

            if (expandedNodes.has(node.id) && node.children) {
                result.children = node.children
                    .filter(child => child)
                    .map(child => processData(child.id))
                    .filter(child => child !== null);
            }

            return result;
        };

        const hierarchyData = processData(rootNode.id);
        if (!hierarchyData) return;

        d3.select(svgRef.current).selectAll("*").remove();

        const svg = d3.select(svgRef.current)
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g")
            .attr("transform", `translate(${centerX},${centerY}) ${currentTransformRef.current}`);

        const tree = d3.tree()
            .size([2 * Math.PI, Math.min(width, height) / 3])
            .separation((a: any, b: any) => (a.parent === b.parent ? 1 : 2) / a.depth);

        const root = tree(d3.hierarchy(hierarchyData));

        const links = g.selectAll(".link")
            .data(root.links())
            .join("path")
            .attr("class", "link")
            .attr("d", d3.linkRadial()
                .angle((d: any) => d.x)
                .radius((d: any) => d.y))
            .style("fill", "none")
            .style("stroke", "#999")
            .style("stroke-opacity", 0.6)
            .style("stroke-width", (d: any) => Math.max(3 - d.target.depth * 0.5, 0.5));

        const nodes = g.selectAll(".node")
            .data(root.descendants())
            .join("g")
            .attr("class", "node")
            .attr("transform", (d: any) => `
                translate(${d.y * Math.sin(d.x)},${-d.y * Math.cos(d.x)})
            `)
            .style("cursor", (d: any) => d.data.nodeData.has_children ? "pointer" : "default")
            .on("click", async (event: any, d: any) => {
                event.stopPropagation();
                const nodeId = d.data.nodeData.id;

                if (d.data.nodeData.has_children) {
                    const newExpanded = new Set(expandedNodes);

                    if (expandedNodes.has(nodeId)) {
                        console.log('Collapsing node:', nodeId);
                        newExpanded.delete(nodeId);
                        const descendantIds = getAllDescendantIds(nodeId, nodesData);
                        descendantIds.forEach(id => newExpanded.delete(id));
                    } else {
                        console.log('Expanding node:', nodeId);
                        newExpanded.add(nodeId);

                        const currentNode = nodesData[nodeId];
                        if (!currentNode?.children) {
                            await fetchNode(nodeId);
                        }
                    }

                    setExpandedNodes(newExpanded);
                }
            });

        nodes.append("circle")
            .attr("r", (d: any) => Math.max(25 / (d.depth + 1), 4))
            .style("fill", (d: any) => nodeColors[d.data.nodeData.node_type])
            .style("stroke", "#fff")
            .style("stroke-width", 1.5);

        nodes.filter((d: any) => d.data.nodeData.has_children)
            .append("text")
            .attr("dy", "0.3em")
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("fill", "white")
            .text((d: any) => expandedNodes.has(d.data.nodeData.id) ? "-" : "+");

        const truncateText = (text: string, maxLength: number = 30) => {
            return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
        };

        nodes.append("text")
            .attr("dy", "0.35em")
            .attr("x", (d: any) => d.children ? -8 : 8)
            .attr("text-anchor", (d: any) => d.children ? "end" : "start")
            .text((d: any) => truncateText(d.data.nodeData.content))
            .style("font-size", (d: any) => `${Math.max(16 / (d.depth + 1), 8)}px`)
            .style("fill", "#333")
            .style("stroke", "white")
            .style("stroke-width", 0.3);

        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event: any) => {
                currentTransformRef.current = event.transform;
                g.attr("transform", `translate(${centerX},${centerY}) ${event.transform}`);
            });

        svg.call(zoom as any);

    }, [expandedNodes, nodesData, rootNode]);

    return (
        <div className="w-full h-full flex justify-center items-center">
            <svg
                ref={svgRef}
                className="border rounded-lg shadow-lg bg-white"
            />
        </div>
    );
};

export default HyperbolicTree;