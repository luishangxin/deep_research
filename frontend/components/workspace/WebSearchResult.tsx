"use client";

import { ExternalLink, Globe, Star } from "lucide-react";
import { motion } from "motion/react";

// ──────────────────────────────────────
// Types
// ──────────────────────────────────────

export interface WebResult {
    title: string;
    url: string;
    content: string;
    score?: number;
    raw_content?: string;
}

interface WebSearchOutputProps {
    results: WebResult[];
    query?: string;
}

// ──────────────────────────────────────
// Helper: extract hostname + favicon
// ──────────────────────────────────────

function getDomain(url: string): string {
    try {
        return new URL(url).hostname.replace(/^www\./, "");
    } catch {
        return url;
    }
}

function getFaviconUrl(url: string): string {
    try {
        const { origin } = new URL(url);
        return `https://www.google.com/s2/favicons?domain=${origin}&sz=32`;
    } catch {
        return "";
    }
}

// ──────────────────────────────────────
// Single source card
// ──────────────────────────────────────

function WebResultCard({ result, index }: { result: WebResult; index: number }) {
    const domain = getDomain(result.url);
    const favicon = getFaviconUrl(result.url);
    const snippet = result.content?.slice(0, 200).trim() ?? "";

    return (
        <motion.a
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
            className="group flex flex-col gap-1.5 p-3 rounded-xl border border-[--bdr] bg-[--bg-surface] hover:border-blue-300 dark:hover:border-blue-500/40 hover:shadow-sm transition-all duration-150 no-underline"
        >
            {/* Source row */}
            <div className="flex items-center gap-1.5">
                {favicon && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={favicon} alt="" className="w-3.5 h-3.5 rounded-sm" onError={(e) => (e.currentTarget.style.display = "none")} />
                )}
                <span className="text-[10px] text-[--text-3] font-medium truncate">{domain}</span>
                {result.score !== undefined && result.score > 0.8 && (
                    <Star className="w-2.5 h-2.5 text-amber-400 fill-amber-400 ml-auto shrink-0" />
                )}
            </div>

            {/* Title */}
            <p className="text-xs font-semibold text-[--text-1] leading-snug group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
                {result.title}
            </p>

            {/* Snippet */}
            {snippet && (
                <p className="text-[11px] text-[--text-3] leading-relaxed line-clamp-2">{snippet}…</p>
            )}

            {/* URL */}
            <div className="flex items-center gap-1 mt-0.5">
                <ExternalLink className="w-2.5 h-2.5 text-[--text-3] shrink-0" />
                <span className="text-[9px] text-[--text-3] truncate">{result.url}</span>
            </div>
        </motion.a>
    );
}

// ──────────────────────────────────────
// Main component
// ──────────────────────────────────────

export function WebSearchOutput({ results, query }: WebSearchOutputProps) {
    if (!results || results.length === 0) return null;

    return (
        <div className="mt-2 mb-1">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <Globe className="w-3.5 h-3.5 text-blue-500" />
                <span className="text-xs font-medium text-[--text-2]">
                    {results.length} web source{results.length > 1 ? "s" : ""}
                    {query && <span className="text-[--text-3] font-normal"> for "{query}"</span>}
                </span>
            </div>

            {/* Cards grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {results.map((r, i) => (
                    <WebResultCard key={r.url ?? i} result={r} index={i} />
                ))}
            </div>
        </div>
    );
}

// ──────────────────────────────────────
// Web Fetch (single page) display
// ──────────────────────────────────────

export function WebFetchOutput({ url, content }: { url: string; content: string }) {
    const domain = getDomain(url);
    const favicon = getFaviconUrl(url);
    const preview = content?.slice(0, 400).trim() ?? "";

    return (
        <div className="mt-2 mb-1 rounded-xl border border-[--bdr] bg-[--bg-surface] overflow-hidden">
            {/* Header bar */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-[--bdr] bg-[--bg-panel]">
                <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                    {favicon && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={favicon} alt="" className="w-3.5 h-3.5 rounded-sm" onError={(e) => (e.currentTarget.style.display = "none")} />
                    )}
                    <span className="text-xs text-[--text-2] font-medium truncate">{domain}</span>
                </div>
                <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-blue-500 hover:text-blue-400 flex items-center gap-0.5 shrink-0"
                >
                    Open <ExternalLink className="w-2.5 h-2.5" />
                </a>
            </div>

            {/* Content preview */}
            <div className="px-3 py-2">
                <p className="text-[11px] text-[--text-3] leading-relaxed line-clamp-4 whitespace-pre-wrap">
                    {preview}{content?.length > 400 ? "…" : ""}
                </p>
                {content && (
                    <p className="text-[9px] text-[--text-3] mt-1">
                        {content.length.toLocaleString()} characters fetched
                    </p>
                )}
            </div>
        </div>
    );
}
