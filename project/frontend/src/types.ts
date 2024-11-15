export interface Node {
    id: string;
    parent_id: string | null;
    node_type: 'SYSTEM' | 'PROMPT' | 'RESPONSE';
    content: string;
    timestamp: string;
    has_children: boolean;
    children?: Node[];
    model_config?: {
        model: string;
        [key: string]: any;
    };
}