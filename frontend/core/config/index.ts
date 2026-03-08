// Configuration helpers for reading environment variables

const GATEWAY_BASE_URL =
    process.env.NEXT_PUBLIC_GATEWAY_BASE_URL || "http://localhost:8000";

const LANGGRAPH_BASE_URL =
    process.env.NEXT_PUBLIC_LANGGRAPH_BASE_URL || "http://localhost:2024";

export function getGatewayBaseURL(): string {
    return GATEWAY_BASE_URL;
}

export function getLangGraphBaseURL(): string {
    return LANGGRAPH_BASE_URL;
}
