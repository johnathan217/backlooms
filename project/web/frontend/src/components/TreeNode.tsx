import React, { useState, useEffect } from 'react';
import { Node } from '../types';
import { fetchNode } from '../api';
import { ChevronRight, ChevronDown, MessageCircle, Settings, User } from 'lucide-react';

interface TreeNodeProps {
  nodeId: string;
  onSelect?: (node: Node) => void;
}

const NodeIcon = ({ type }: { type: Node['node_type'] }) => {
  switch (type) {
    case 'SYSTEM':
      return <Settings className="w-4 h-4 text-yellow-500" />;
    case 'PROMPT':
      return <User className="w-4 h-4 text-blue-500" />;
    case 'RESPONSE':
      return <MessageCircle className="w-4 h-4 text-green-500" />;
  }
};

export const TreeNode: React.FC<TreeNodeProps> = ({ nodeId, onSelect }) => {
  const [node, setNode] = useState<Node | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNode(nodeId)
      .then(setNode)
      .catch(err => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [nodeId]);

  if (isLoading) return <div className="ml-4 p-2">Loading...</div>;
  if (error) return <div className="ml-4 p-2 text-red-500">Error: {error}</div>;
  if (!node) return null;

  return (
    <div className="ml-4">
      <div className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded cursor-pointer">
        {node.has_children && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-1 hover:bg-gray-200 rounded"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}
        <div
          className="flex items-center gap-2 flex-1"
          onClick={() => onSelect?.(node)}
        >
          <NodeIcon type={node.node_type} />
          <span className="truncate">{node.content}</span>
        </div>
      </div>

      {isExpanded && node.children?.map(child => (
        <TreeNode
          key={child.id}
          nodeId={child.id}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
};