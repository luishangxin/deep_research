"use client";

import { useState, useRef, useCallback } from "react";
import { getLangGraphBaseURL } from "@/core/config";
import type { Message, AgentMode } from "@/core/models/types";
import { v4 as uuidv4 } from "uuid";

export interface StreamOptions {
    threadId: string;
    mode?: AgentMode;
    onStart?: () => void;
    onFinish?: (messages: Message[]) => void;
}

export interface StreamState {
    messages: Message[];
    isStreaming: boolean;
    error: string | null;
}

function buildContext(mode: AgentMode) {
    return {
        mode,
        thinking_enabled: mode !== "flash",
        is_plan_mode: mode === "pro" || mode === "ultra",
        subagent_enabled: mode === "ultra",
    };
}

export function useThreadStream({ threadId, mode = "flash", onStart, onFinish }: StreamOptions) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const abortRef = useRef<AbortController | null>(null);

    const sendMessage = useCallback(
        async (content: string) => {
            if (!content.trim() || isStreaming) return;

            // Optimistic: add human message immediately
            const humanMsg: Message = {
                id: uuidv4(),
                type: "human",
                content,
            };
            setMessages((prev) => [...prev, humanMsg]);
            setIsStreaming(true);
            setError(null);
            onStart?.();

            // Placeholder AI message that we stream into
            const aiId = uuidv4();
            setMessages((prev) => [
                ...prev,
                { id: aiId, type: "ai", content: "" } as Message,
            ]);

            abortRef.current = new AbortController();
            const base = getLangGraphBaseURL();

            try {
                const res = await fetch(`${base}/runs/stream`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    signal: abortRef.current.signal,
                    body: JSON.stringify({
                        assistant_id: "agent",
                        thread_id: threadId,
                        input: {
                            messages: [{ role: "human", content }],
                        },
                        config: { configurable: { context: buildContext(mode) } },
                        stream_mode: ["values", "messages-tuple"],
                    }),
                });

                if (!res.ok) {
                    throw new Error(`Stream error: ${res.status}`);
                }

                const reader = res.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = "";
                let currentText = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() ?? "";

                    for (const line of lines) {
                        if (!line.startsWith("data: ")) continue;
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr || jsonStr === "[DONE]") continue;

                        try {
                            const event = JSON.parse(jsonStr);
                            // messages-tuple stream: [type, message_chunk]
                            if (Array.isArray(event) && event.length === 2) {
                                const [_type, chunk] = event;
                                if (chunk?.type === "AIMessageChunk" || chunk?.type === "AIMessage") {
                                    const chunkContent = chunk.content;
                                    if (typeof chunkContent === "string") {
                                        currentText += chunkContent;
                                    } else if (Array.isArray(chunkContent)) {
                                        for (const part of chunkContent) {
                                            if (part?.type === "text") currentText += part.text ?? "";
                                        }
                                    }
                                    setMessages((prev) =>
                                        prev.map((m) =>
                                            m.id === aiId ? { ...m, content: currentText } : m
                                        )
                                    );
                                }
                            }
                            // values stream: full thread state
                            else if (event?.messages && Array.isArray(event.messages)) {
                                const serverMsgs: Message[] = event.messages.map(
                                    (m: Record<string, unknown>) => ({
                                        id: (m.id as string) || uuidv4(),
                                        type: (m.type as string) === "human" ? "human" : "ai",
                                        content: m.content as string,
                                        tool_calls: (m.tool_calls as Message["tool_calls"]) ?? [],
                                        additional_kwargs: (m.additional_kwargs as Record<string, unknown>) ?? {},
                                    })
                                );
                                // Replace entire message list with authoritative server state
                                setMessages(serverMsgs);
                            }
                        } catch {
                            // Ignore parse errors for partial chunks
                        }
                    }
                }

                // Finalize with current messages
                setMessages((prev) => {
                    onFinish?.(prev);
                    return prev;
                });
            } catch (err) {
                if ((err as Error).name === "AbortError") return;
                const msg = err instanceof Error ? err.message : "Stream failed";
                setError(msg);
                setMessages((prev) => prev.filter((m) => m.id !== aiId));
            } finally {
                setIsStreaming(false);
                abortRef.current = null;
            }
        },
        [threadId, mode, isStreaming, onStart, onFinish]
    );

    const stopStream = useCallback(() => {
        abortRef.current?.abort();
        setIsStreaming(false);
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
        setError(null);
    }, []);

    return { messages, isStreaming, error, sendMessage, stopStream, clearMessages };
}
