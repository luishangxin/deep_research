"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Send, Square, Zap, Cpu, Rocket, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentMode } from "@/core/models/types";

interface ChatInputProps {
    onSend: (content: string) => void;
    onStop?: () => void;
    isStreaming: boolean;
    disabled?: boolean;
    mode: AgentMode;
    onModeChange: (mode: AgentMode) => void;
}

const MODES: { value: AgentMode; label: string; icon: typeof Zap; description: string }[] = [
    { value: "flash", label: "Flash", icon: Zap, description: "Fast & efficient" },
    { value: "pro", label: "Pro", icon: Cpu, description: "Balanced, with planning" },
    { value: "ultra", label: "Ultra", icon: Rocket, description: "Deep research, multi-agent" },
];

export function ChatInput({
    onSend, onStop, isStreaming, disabled, mode, onModeChange,
}: ChatInputProps) {
    const [value, setValue] = useState("");
    const [modeOpen, setModeOpen] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const currentMode = MODES.find((m) => m.value === mode) ?? MODES[0];

    const handleSend = () => {
        const trimmed = value.trim();
        if (!trimmed || isStreaming || disabled) return;
        onSend(trimmed);
        setValue("");
        if (textareaRef.current) textareaRef.current.style.height = "auto";
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setValue(e.target.value);
        const ta = e.target;
        ta.style.height = "auto";
        ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
    };

    return (
        <div className="relative w-full max-w-3xl mx-auto">
            <div className={cn(
                "relative rounded-2xl border bg-[--bg-surface] shadow-sm",
                "border-black/10 dark:border-white/10",
                "transition-all duration-200",
                !disabled && "hover:border-black/15 dark:hover:border-white/15",
                !disabled && "focus-within:border-violet-400 focus-within:shadow-violet-200/30 dark:focus-within:border-violet-500/50 dark:focus-within:shadow-violet-500/10 focus-within:shadow-lg"
            )}>
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    disabled={disabled || isStreaming}
                    placeholder="Ask anything… (Shift+Enter for newline)"
                    rows={1}
                    className={cn(
                        "w-full resize-none bg-transparent px-4 pt-4 pb-12 text-sm",
                        "text-[--text-primary] placeholder:text-[--text-muted]",
                        "outline-none scrollbar-thin disabled:opacity-50"
                    )}
                />

                {/* Bottom toolbar */}
                <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 pb-2.5 gap-2">
                    {/* Mode Selector */}
                    <div className="relative">
                        <button
                            onClick={() => setModeOpen((o) => !o)}
                            className={cn(
                                "flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs font-medium",
                                "bg-black/5 hover:bg-black/8 dark:bg-white/5 dark:hover:bg-white/10",
                                "border border-black/8 hover:border-black/12 dark:border-white/10 dark:hover:border-white/20",
                                "text-[--text-secondary] hover:text-[--text-primary] transition-all"
                            )}
                        >
                            <currentMode.icon className="w-3 h-3" />
                            <span>{currentMode.label}</span>
                            <ChevronDown className={cn("w-3 h-3 transition-transform", modeOpen && "rotate-180")} />
                        </button>

                        <AnimatePresence>
                            {modeOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: 4, scale: 0.96 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 4, scale: 0.96 }}
                                    transition={{ duration: 0.12 }}
                                    className="absolute bottom-full mb-2 left-0 w-44 rounded-xl border border-black/8 dark:border-white/10 bg-[--bg-surface] shadow-xl overflow-hidden"
                                >
                                    {MODES.map((m) => (
                                        <button
                                            key={m.value}
                                            onClick={() => { onModeChange(m.value); setModeOpen(false); }}
                                            className={cn(
                                                "w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors",
                                                m.value === mode
                                                    ? "bg-violet-600 text-white"
                                                    : "hover:bg-black/5 dark:hover:bg-white/5 text-[--text-secondary] hover:text-[--text-primary]"
                                            )}
                                        >
                                            <m.icon className="w-3.5 h-3.5 shrink-0" />
                                            <div>
                                                <div className="text-xs font-medium">{m.label}</div>
                                                <div className="text-[10px] text-[--text-muted]">{m.description}</div>
                                            </div>
                                        </button>
                                    ))}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Send / Stop */}
                    <button
                        onClick={isStreaming ? onStop : handleSend}
                        disabled={!isStreaming && (!value.trim() || disabled)}
                        className={cn(
                            "flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-150",
                            isStreaming
                                ? "bg-red-100 dark:bg-red-500/20 hover:bg-red-200 dark:hover:bg-red-500/30 text-red-500 dark:text-red-400 border border-red-200 dark:border-red-500/30"
                                : value.trim() && !disabled
                                    ? "bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-200 dark:shadow-violet-500/30"
                                    : "bg-black/5 dark:bg-white/5 text-[--text-muted] cursor-not-allowed border border-[--border]"
                        )}
                    >
                        {isStreaming ? <Square className="w-3.5 h-3.5" /> : <Send className="w-3.5 h-3.5" />}
                    </button>
                </div>
            </div>

            <p className="text-center text-[10px] text-[--text-muted] mt-2">
                Flow can make mistakes. Verify important information.
            </p>
        </div>
    );
}
