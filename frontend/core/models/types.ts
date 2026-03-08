// Core TypeScript interfaces for the flow Agent frontend

export type AgentMode = "flash" | "pro" | "ultra";

export interface Thread {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
    metadata: Record<string, unknown>;
    task_count: number;
}

export interface ToolCall {
    id: string;
    name: string;
    args: Record<string, unknown>;
    output?: string;
    error?: string;
    status: "pending" | "running" | "done" | "error";
}

export interface MessageContent {
    type: "text" | "tool_use" | "tool_result" | "thinking";
    text?: string;
    id?: string;
    name?: string;
    input?: Record<string, unknown>;
    content?: string;
    thinking?: string;
}

export interface Message {
    id: string;
    type: "human" | "ai" | "tool" | "system";
    content: string | MessageContent[];
    tool_calls?: ToolCall[];
    additional_kwargs?: Record<string, unknown>;
    response_metadata?: Record<string, unknown>;
}

export interface AgentContext {
    mode: AgentMode;
    thinking_enabled: boolean;
    is_plan_mode: boolean;
    subagent_enabled: boolean;
}

export interface ModelInfo {
    name: string;
    display_name: string;
    supports_thinking: boolean;
    supports_vision: boolean;
}

export interface ToolInfo {
    name: string;
    group: string | null;
    use: string;
}

export interface StreamMessage {
    type: string;
    content?: string;
    tool_calls?: ToolCall[];
    [key: string]: unknown;
}
