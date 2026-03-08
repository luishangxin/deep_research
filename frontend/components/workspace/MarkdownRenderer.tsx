"use client";

import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import { cn } from "@/lib/utils";

export const MarkdownRenderer = memo(function MarkdownRenderer({
    content,
    className,
}: {
    content: string;
    className?: string;
}) {
    return (
        <div className={cn("prose prose-sm max-w-none text-[--text-secondary]", className)}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw]}
                components={{
                    code({ className, children }) {
                        const isInline = !className;
                        if (isInline) {
                            return (
                                <code className="px-1.5 py-0.5 rounded-md bg-violet-50 dark:bg-white/10 font-mono text-[0.8em] text-violet-600 dark:text-violet-300">
                                    {children}
                                </code>
                            );
                        }
                        return <CodeBlock className={className}>{children}</CodeBlock>;
                    },
                    a({ href, children }) {
                        return (
                            <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-violet-600 dark:text-violet-400 hover:text-violet-500 dark:hover:text-violet-300 underline underline-offset-2 transition-colors"
                            >
                                {children}
                            </a>
                        );
                    },
                    blockquote({ children }) {
                        return (
                            <blockquote className="border-l-2 border-violet-400 pl-4 text-[--text-muted] italic">
                                {children}
                            </blockquote>
                        );
                    },
                    table({ children }) {
                        return (
                            <div className="overflow-x-auto my-3">
                                <table className="w-full text-sm border border-[--border] rounded-lg overflow-hidden">
                                    {children}
                                </table>
                            </div>
                        );
                    },
                    th({ children }) {
                        return (
                            <th className="px-3 py-2 bg-black/4 dark:bg-white/5 text-left text-[--text-secondary] font-medium border-b border-[--border]">
                                {children}
                            </th>
                        );
                    },
                    td({ children }) {
                        return (
                            <td className="px-3 py-2 border-b border-[--border] text-[--text-muted]">
                                {children}
                            </td>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
});

function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
    const [copied, setCopied] = React.useState(false);
    const language = className?.replace("language-", "") ?? "text";
    const code = String(children).replace(/\n$/, "");

    const handleCopy = () => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="group relative my-3 rounded-xl overflow-hidden border border-[--border]">
            <div className="flex items-center justify-between px-4 py-2 bg-black/4 dark:bg-zinc-800/80 border-b border-[--border]">
                <span className="text-xs text-[--text-muted] font-mono">{language}</span>
                <button
                    onClick={handleCopy}
                    className="text-xs text-[--text-muted] hover:text-[--text-primary] transition-colors"
                >
                    {copied ? "Copied!" : "Copy"}
                </button>
            </div>
            <pre className="overflow-x-auto p-4 bg-gray-50 dark:bg-zinc-900/80 text-sm">
                <code className="font-mono text-gray-800 dark:text-green-300/90">{children}</code>
            </pre>
        </div>
    );
}
