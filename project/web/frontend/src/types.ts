export type NodeType = 'SYSTEM' | 'PROMPT' | 'RESPONSE';

export interface Node {
    id: string;
    content: string;
    node_type: NodeType;
    model_config: Record<string, any>;
    timestamp: string;
    parent_id: string | null;
    has_children: boolean;
    children?: Node[];
}