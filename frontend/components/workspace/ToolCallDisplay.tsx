"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
    ChevronDown, Terminal, CheckCircle2, XCircle,
    Loader2, Eye, EyeOff, Globe, FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolCall } from "@/core/models/types";
import { ToolResultRenderer } from "./ToolResultRenderer";

// ──────────────────────────────────────
// Tool icon + label helpers
// ──────────────────────────────────────

const TOOL_META: Record<string, { icon: React.ElementType; label: string; color: string }> = {
    web_search: { icon: Globe, label: "Web Search", color: "text-blue-500" },
    web_fetch: { icon: Globe, label: "Web Fetch", color: "text-blue-400" },
    pubmed_search: { icon: FlaskConical, label: "PubMed Search", color: "text-green-500" },
    pubmed_fetch: { icon: FlaskConical, label: "PubMed Fetch", color: "text-green-400" },
};

function getToolMeta(name: string) {
    return TOOL_META[name] ?? { icon: Terminal, label: name, color: "text-[--text-3]" };
}

// ──────────────────────────────────────
// ToolCallDisplay
// ──────────────────────────────────────

export function ToolCallDisplay({ toolCalls }: { toolCalls: ToolCall[] }) {
    if (!toolCalls || toolCalls.length === 0) return null;
    return (
        <div className="my-2 space-y-2">
            {toolCalls.map((tc) => <ToolCallItem key={tc.id} toolCall={tc} />)}
        </div>
    );
}

function ToolCallItem({ toolCall }: { toolCall: ToolCall }) {
    const [expanded, setExpanded] = useState(false);
    const meta = getToolMeta(toolCall.name);
    const Icon = meta.icon;

    const hasRichOutput = !!toolCall.output && toolCall.status === "done";
    const isKnownTool = toolCall.name in TOOL_META;

    const statusIcon = {
        pending: <Loader2 className="w-3.5 h-3.5 animate-spin text-yellow-500" />,
        running: <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />,
        done: <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />,
        error: <XCircle className="w-3.5 h-3.5 text-red-500" />,
    }[toolCall.status ?? "done"];

    // For known rich tools, render the result inline (expanded by default when done)
    const defaultExpanded = isKnownTool && hasRichOutput;
    const [open, setOpen] = useState(defaultExpanded);

    return (
        <div className="rounded-xl border border-[--bdr] bg-[--bg-panel] overflow-hidden">
            {/* Header row */}
            <button
                onClick={() => setOpen((o) => !o)}
                className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-black/4 dark:hover:bg-white/5 transition-colors text-left"
            >
                <Icon className={cn("w-3.5 h-3.5 shrink-0", meta.color)} />
                <span className="text-xs font-medium text-[--text-2] flex-1 truncate">{meta.label}</span>

                {/* Query/args summary */}
                {toolCall.args && (
                    <span className="text-[10px] text-[--text-3] truncate max-w-[160px]">
                        {(toolCall.args.query as string)
                            ?? (toolCall.args.url as string)
                            ?? (toolCall.args.pmid as string)
                            ?? ""}
                    </span>
                )}

                {statusIcon}
                <ChevronDown className={cn("w-3.5 h-3.5 text-[--text-3] transition-transform shrink-0", open && "rotate-180")} />
            </button>

            {/* Expanded content */}
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        key="content"
                        initial={{ height: 0 }}
                        animate={{ height: "auto" }}
                        exit={{ height: 0 }}
                        transition={{ duration: 0.18, ease: "easeInOut" }}
                        className="overflow-hidden"
                    >
                        <div className="border-t border-[--bdr] px-3 py-2 space-y-2">
                            {/* Args (always show for non-rich tools) */}
                            {!isKnownTool && toolCall.args && Object.keys(toolCall.args).length > 0 && (
                                <div>
                                    <p className="text-[10px] text-[--text-3] uppercase tracking-wider mb-1">Input</p>
                                    <pre className="text-xs font-mono text-[--text-2] bg-[--bg-panel] rounded-lg p-2 overflow-x-auto whitespace-pre-wrap border border-[--bdr]">
                                        {JSON.stringify(toolCall.args, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Rich result renderer */}
                            {hasRichOutput && (
                                <ToolResultRenderer
                                    toolName={toolCall.name}
                                    output={toolCall.output!}
                                    args={toolCall.args}
                                />
                            )}

                            {/* Error */}
                            {toolCall.error && (
                                <div>
                                    <p className="text-[10px] text-red-500 uppercase tracking-wider mb-1">Error</p>
                                    <pre className="text-xs font-mono text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/20 rounded-lg p-2 overflow-x-auto whitespace-pre-wrap border border-red-200 dark:border-red-500/20">
                                        {toolCall.error}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ──────────────────────────────────────
// Thinking block (unchanged)
// ──────────────────────────────────────

export function ThinkingBlock({ content }: { content: string }) {
    const [visible, setVisible] = useState(false);
    if (!content) return null;

    return (
        <div className="my-2 rounded-xl border border-violet-200 dark:border-violet-500/20 bg-violet-50 dark:bg-violet-500/5 overflow-hidden">
            <button
                onClick={() => setVisible((o) => !o)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-violet-100/50 dark:hover:bg-violet-500/10 transition-colors text-left"
            >
                <div className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
                <span className="text-xs text-violet-600 dark:text-violet-300 flex-1">Thinking</span>
                {visible
                    ? <EyeOff className="w-3.5 h-3.5 text-violet-400" />
                    : <Eye className="w-3.5 h-3.5 text-violet-400" />}
            </button>
            <AnimatePresence>
                {visible && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: "auto" }}
                        exit={{ height: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden"
                    >
                        <div className="border-t border-violet-200 dark:border-violet-500/10 px-3 py-2">
                            <p className="text-xs text-violet-700 dark:text-violet-200/50 whitespace-pre-wrap font-mono leading-relaxed">
                                {content}
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
