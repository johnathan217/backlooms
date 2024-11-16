import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useNodeStore } from '../nodeStore';
import { Node } from '../types';
import { api } from '../api';

export const Tree: React.FC = () => {
    const svgRef = useRef<SVGSVGElement>(null);
    const currentTransformRef = useRef(d3.zoomIdentity);
    const { nodesData, selectedNodeId, expandedNodes, handleNodeClick } = useNodeStore();
    const [descendantCounts, setDescendantCounts] = useState<Record<string, number>>({});

    const nodeColors: Record<Node['node_type'], string> = {
        'SYSTEM': '#ff4444',
        'PROMPT': '#4444ff',
        'RESPONSE': '#44ff44'
    };

    const fetchDescendantCount = async (nodeId: string) => {
        if (descendantCounts[nodeId] === undefined) {
            try {
                const count = await api.fetchDescendantCount(nodeId);
                setDescendantCounts(prev => ({
                    ...prev,
                    [nodeId]: count
                }));
            } catch (error) {
                console.error('Failed to fetch descendant count:', nodeId, error);
            }
        }
    };

    const processData = (nodeId: string) => {
        const node = nodesData[nodeId];
        if (!node) return null;

        fetchDescendantCount(nodeId);

        return {
            name: node.id,
            nodeData: node,
            totalDescendants: descendantCounts[nodeId] ?? 1,
            children: expandedNodes.has(node.id) && node.children
                ? node.children
                    .map(child => processData(child.id))
                    .filter(Boolean)
                : []
        };
    };

    const findMaxDepth = (root: d3.HierarchyNode<any>): number => {
        let maxDepth = root.depth;
        root.each(node => {
            maxDepth = Math.max(maxDepth, node.depth);
        });
        return maxDepth;
    };

    const shouldShowText = (d: any, maxDepth: number) => {
        return d.depth >= maxDepth - 2;
    };

    const calculateStrokeWidth = (d: any) => {
        const minWidth = 0.5;
        const maxWidth = 8;
        const descendantCount = d.target.data.totalDescendants;

        const width = Math.log2(descendantCount + 1) * 1.5;
        const depthScale = Math.max(0.3, 1 - (d.target.depth * 0.15));

        return Math.max(minWidth, Math.min(maxWidth, width * depthScale));
    };

    useEffect(() => {
        console.log('Tree effect triggered:', {
            nodesCount: Object.keys(nodesData).length,
            expandedNodesCount: expandedNodes.size,
            selectedNodeId
        });

        if (!svgRef.current) return;

        const rootNodeId = Object.keys(nodesData)[0];
        if (!rootNodeId) return;

        const width = 800;
        const height = 600;
        const centerX = width / 2;
        const centerY = height / 2;

        d3.select(svgRef.current).selectAll("*").remove();

        const svg = d3.select(svgRef.current)
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g")
            .attr("transform", `translate(${centerX},${centerY}) ${currentTransformRef.current}`);

        const tree = d3.tree()
            .size([2 * Math.PI, Math.min(width, height) / 3])
            .separation((a: any, b: any) => (a.parent === b.parent ? 1 : 2) / a.depth);

        const hierarchyData = processData(rootNodeId);
        if (!hierarchyData) return;

        const root = tree(d3.hierarchy(hierarchyData));
        const maxDepth = findMaxDepth(root);

        const gradient = svg.append("defs")
            .append("linearGradient")
            .attr("id", "branch-gradient")
            .attr("gradientUnits", "userSpaceOnUse");

        gradient.append("stop")
            .attr("offset", "0%")
            .attr("stop-color", "#666");

        gradient.append("stop")
            .attr("offset", "100%")
            .attr("stop-color", "#999");

        const links = g.selectAll(".link")
            .data(root.links())
            .join("path")
            .attr("class", "link")
            .attr("d", d3.linkRadial()
                .angle((d: any) => d.x)
                .radius((d: any) => d.y))
            .style("fill", "none")
            .style("stroke", "url(#branch-gradient)")
            .style("stroke-opacity", 0.6)
            .style("stroke-width", calculateStrokeWidth)
            .style("stroke-linecap", "round")
            .append("title")
            .text((d: any) => `${d.target.data.totalDescendants} descendants`);

        const nodes = g.selectAll(".node")
            .data(root.descendants())
            .join("g")
            .attr("class", "node")
            .attr("transform", (d: any) =>
                `translate(${d.y * Math.sin(d.x)},${-d.y * Math.cos(d.x)})`)
            .style("cursor", "pointer")
            .on("click", (event: any, d: any) => {
                event.stopPropagation();
                handleNodeClick(d.data.nodeData.id);
            });

        nodes.append("circle")
            .attr("r", (d: any) => Math.max(25 / (d.depth + 1), 4))
            .style("fill", (d: any) => nodeColors[d.data.nodeData.node_type])
            .style("stroke", (d: any) =>
                d.data.nodeData.id === selectedNodeId ? "#000" : "#fff")
            .style("stroke-width", (d: any) =>
                d.data.nodeData.id === selectedNodeId ? 2 : 1.5);

        nodes.filter((d: any) => d.data.nodeData.has_children)
            .append("text")
            .attr("dy", "0.3em")
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("fill", "white")
            .text((d: any) => expandedNodes.has(d.data.nodeData.id) ? "-" : "+");

        const truncateText = (text: string) =>
            text.length > 30 ? text.substring(0, 30) + "..." : text;

        nodes.filter((d: any) => shouldShowText(d, maxDepth))
            .append("text")
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

    }, [nodesData, expandedNodes, selectedNodeId, descendantCounts]);

    return (
        <svg
            ref={svgRef}
            className="w-full h-full border rounded-lg shadow-lg bg-white"
        />
    );
};