"use client";

import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import type { Message } from "@/core/models/types";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
    messages: Message[];
    isStreaming: boolean;
    className?: string;
}

export function MessageList({ messages, isStreaming, className }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const isAtBottomRef = useRef(true);

    // Track scroll position
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        const onScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
        };
        container.addEventListener("scroll", onScroll, { passive: true });
        return () => container.removeEventListener("scroll", onScroll);
    }, []);

    // Auto-scroll during streaming
    useEffect(() => {
        if (isAtBottomRef.current) {
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages]);

    if (messages.length === 0) return null;

    return (
        <div
            ref={containerRef}
            className={cn("flex flex-col overflow-y-auto scrollbar-thin py-4", className)}
        >
            <div className="max-w-3xl mx-auto w-full">
                {messages.map((message, idx) => (
                    <MessageItem
                        key={message.id}
                        message={message}
                        isLast={idx === messages.length - 1}
                    />
                ))}

                {/* Streaming indicator at the bottom */}
                {isStreaming && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="px-4 pb-2"
                    >
                        <div className="flex gap-1 ml-10">
                            {[0, 1, 2].map((i) => (
                                <motion.div
                                    key={i}
                                    className="w-1.5 h-1.5 rounded-full bg-violet-400"
                                    animate={{ scale: [1, 1.4, 1], opacity: [0.5, 1, 0.5] }}
                                    transition={{
                                        repeat: Infinity,
                                        duration: 1,
                                        delay: i * 0.2,
                                        ease: "easeInOut",
                                    }}
                                />
                            ))}
                        </div>
                    </motion.div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    );
}
