"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { Brain, AlertCircle } from "lucide-react";
import { ChatInput } from "@/components/workspace/ChatInput";
import { MessageList } from "@/components/workspace/MessageList";
import { useThreadStream } from "@/core/threads/stream";
import type { AgentMode } from "@/core/models/types";
import { cn } from "@/lib/utils";

interface ChatPageProps {
    params: Promise<{ thread_id: string }>;
}

export default function ChatPage({ params }: ChatPageProps) {
    const searchParams = useSearchParams();
    const [threadId, setThreadId] = useState<string>("");
    const [mode, setMode] = useState<AgentMode>("flash");

    useEffect(() => {
        params.then((p) => setThreadId(p.thread_id));
    }, [params]);

    const { messages, isStreaming, error, sendMessage, stopStream } = useThreadStream({
        threadId: threadId || "new",
        mode,
    });

    useEffect(() => {
        const q = searchParams?.get("q");
        if (q && threadId && messages.length === 0) {
            const timer = setTimeout(() => sendMessage(q), 300);
            return () => clearTimeout(timer);
        }
    }, [threadId, searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

    const isEmpty = messages.length === 0 && !isStreaming;

    return (
        <div className="flex flex-col h-full bg-[--bg-base]">
            {/* Top bar */}
            <div className="flex items-center h-12 px-4 border-b border-[--border] shrink-0 bg-[--bg-surface]">
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                        <Brain className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-sm font-medium text-[--text-muted]">
                        {threadId === "new" ? "New Conversation" : "Chat"}
                    </span>
                </div>
            </div>

            {/* Messages area */}
            <div className="flex-1 overflow-hidden relative">
                {isEmpty ? (
                    <EmptyState onSuggestion={sendMessage} />
                ) : (
                    <MessageList messages={messages} isStreaming={isStreaming} className="h-full" />
                )}

                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 dark:bg-red-900/80 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-200 text-sm shadow-lg"
                    >
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        {error}
                    </motion.div>
                )}
            </div>

            {/* Input */}
            <div className="shrink-0 pb-4 px-4 pt-3 border-t border-[--border] bg-[--bg-base]">
                <ChatInput
                    onSend={sendMessage}
                    onStop={stopStream}
                    isStreaming={isStreaming}
                    mode={mode}
                    onModeChange={setMode}
                />
            </div>
        </div>
    );
}

const QUICK_ACTIONS = [
    "Explain this concept step-by-step",
    "Write a Python script to automate this",
    "Research and summarize the latest papers on",
    "Create a detailed plan for",
];

function EmptyState({ onSuggestion }: { onSuggestion: (s: string) => void }) {
    return (
        <div className="flex flex-col items-center justify-center h-full px-6">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
                className="text-center mb-8"
            >
                <div className="relative inline-block mb-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center shadow-lg shadow-violet-200 dark:shadow-violet-500/20">
                        <Brain className="w-6 h-6 text-white" />
                    </div>
                </div>
                <h2 className="text-xl font-semibold text-[--text-primary] mb-2">How can I help?</h2>
                <p className="text-sm text-[--text-muted] max-w-sm">
                    Ask a question, start research, or get help with code.
                </p>
            </motion.div>

            <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
                {QUICK_ACTIONS.map((action, i) => (
                    <motion.button
                        key={action}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 + i * 0.05 }}
                        onClick={() => onSuggestion(action)}
                        className={cn(
                            "px-3 py-2.5 rounded-xl border border-[--border] bg-[--bg-surface]",
                            "hover:bg-[--bg-panel] hover:border-black/12 dark:hover:border-white/15",
                            "text-xs text-[--text-muted] hover:text-[--text-secondary]",
                            "text-left transition-all duration-150 leading-relaxed shadow-xs"
                        )}
                    >
                        {action}
                    </motion.button>
                ))}
            </div>
        </div>
    );
}
