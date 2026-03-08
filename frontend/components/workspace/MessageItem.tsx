"use client";

import { motion } from "motion/react";
import { User, Flame, Copy, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Message } from "@/core/models/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ToolCallDisplay, ThinkingBlock } from "./ToolCallDisplay";

interface MessageItemProps {
    message: Message;
    isLast?: boolean;
}

function getTextContent(content: string | unknown[]): string {
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
        return content.map((part) => {
            if (typeof part === "string") return part;
            if (typeof part === "object" && part !== null) {
                const p = part as Record<string, unknown>;
                if (p.type === "text") return (p.text as string) ?? "";
            }
            return "";
        }).join("");
    }
    return "";
}

function getThinkingContent(content: string | unknown[]): string {
    if (!Array.isArray(content)) return "";
    for (const part of content) {
        if (typeof part === "object" && part !== null) {
            const p = part as Record<string, unknown>;
            if (p.type === "thinking") return (p.thinking as string) ?? "";
        }
    }
    return "";
}

function StreamingCursor() {
    return (
        <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ repeat: Infinity, duration: 1, ease: "easeInOut" }}
            className="inline-block w-2 h-4 ml-0.5 bg-violet-500 rounded-sm align-middle"
        />
    );
}

export function MessageItem({ message, isLast }: MessageItemProps) {
    const [copied, setCopied] = useState(false);
    const isHuman = message.type === "human";
    const textContent = getTextContent(message.content as string | unknown[]);
    const thinkingContent = getThinkingContent(message.content as string | unknown[]);
    const isEmpty = !textContent && (!message.tool_calls || message.tool_calls.length === 0);
    const isStreaming = isLast && !isHuman && isEmpty;

    const handleCopy = () => {
        navigator.clipboard.writeText(textContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (isHuman) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="flex justify-end px-4 pb-4"
            >
                <div className="flex items-end gap-2 max-w-[80%]">
                    <div className="px-4 py-3 rounded-2xl rounded-br-sm bg-violet-600 text-white text-sm leading-relaxed shadow-sm">
                        {textContent || "…"}
                    </div>
                    <div className="w-7 h-7 rounded-full bg-gray-200 dark:bg-zinc-700 flex items-center justify-center shrink-0">
                        <User className="w-3.5 h-3.5 text-gray-500 dark:text-white/60" />
                    </div>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="flex gap-3 px-4 pb-4 group"
        >
            <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-500 rounded-md flex items-center justify-center shrink-0 shadow-sm">
                <Flame className="w-3.5 h-3.5 text-white" />
            </div>

            <div className="flex-1 min-w-0 max-w-[90%]">
                {thinkingContent && <ThinkingBlock content={thinkingContent} />}

                {message.tool_calls && message.tool_calls.length > 0 && (
                    <ToolCallDisplay toolCalls={message.tool_calls} />
                )}

                {textContent ? (
                    <div className="relative">
                        <MarkdownRenderer content={textContent} />
                        <button
                            onClick={handleCopy}
                            className="absolute -top-1 right-0 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity bg-[--bg-surface] border border-[--border] text-[--text-muted] hover:text-[--text-primary] shadow-sm"
                            title="Copy"
                        >
                            {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                    </div>
                ) : isStreaming ? (
                    <div className="flex items-center gap-2 py-2">
                        <StreamingCursor />
                    </div>
                ) : null}
            </div>
        </motion.div>
    );
}
