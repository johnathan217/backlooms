import React from 'react';
import { Node } from '../types';
import { MessageCircle, Settings, User } from 'lucide-react';

interface NodeDetailsProps {
  node: Node;
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

export const NodeDetails: React.FC<NodeDetailsProps> = ({ node }) => {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-4">
        <NodeIcon type={node.node_type} />
        <h2 className="text-lg font-semibold">{node.node_type}</h2>
      </div>

      <div className="space-y-4">
        <div>
          <h3 className="font-medium mb-1">Content</h3>
          <p className="whitespace-pre-wrap bg-gray-50 p-2 rounded">
            {node.content}
          </p>
        </div>

        <div>
          <h3 className="font-medium mb-1">Model Config</h3>
          <pre className="bg-gray-50 p-2 rounded text-sm">
            {JSON.stringify(node.model_config, null, 2)}
          </pre>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <h3 className="font-medium mb-1">ID</h3>
            <p className="text-sm font-mono">{node.id}</p>
          </div>
          <div>
            <h3 className="font-medium mb-1">Parent ID</h3>
            <p className="text-sm font-mono">{node.parent_id || 'Root'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};