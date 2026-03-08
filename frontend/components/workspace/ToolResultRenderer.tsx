"use client";

import { WebSearchOutput, WebFetchOutput, type WebResult } from "./WebSearchResult";
import { PubMedOutput, type PubMedArticle } from "./PubMedResult";

/**
 * Parses the raw string output from a tool call and tries to decode JSON.
 * Falls back to raw string if parsing fails.
 */
function tryParse(raw: string): unknown {
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return raw;
    }
}

interface Props {
    toolName: string;
    output: string;
    args?: Record<string, unknown>;
}

/**
 * Detects the tool type from the tool name and renders the appropriate
 * rich result card (web search, pubmed, etc.)
 * Falls back to raw pre-formatted text if the tool is unknown.
 */
export function ToolResultRenderer({ toolName, output, args }: Props) {
    const parsed = tryParse(output);

    // ── web_search ────────────────────────────
    if (toolName === "web_search") {
        const query = (args?.query as string) ?? (args?.q as string) ?? "";
        let results: WebResult[] = [];

        if (Array.isArray(parsed)) {
            results = parsed as WebResult[];
        } else if (parsed && typeof parsed === "object") {
            const obj = parsed as Record<string, unknown>;
            results = (obj.results as WebResult[]) ?? (obj.data as WebResult[]) ?? [];
        }

        return <WebSearchOutput results={results} query={query} />;
    }

    // ── web_fetch ─────────────────────────────
    if (toolName === "web_fetch") {
        const url = (args?.url as string) ?? "";
        let content = "";
        if (typeof parsed === "string") {
            content = parsed;
        } else if (parsed && typeof parsed === "object") {
            const obj = parsed as Record<string, unknown>;
            content = (obj.content as string) ?? (obj.text as string) ?? output;
        }
        return <WebFetchOutput url={url} content={content} />;
    }

    // ── pubmed_search ─────────────────────────
    if (toolName === "pubmed_search") {
        const query = (args?.query as string) ?? "";
        let articles: PubMedArticle[] = [];

        if (Array.isArray(parsed)) {
            articles = parsed as PubMedArticle[];
        } else if (parsed && typeof parsed === "object") {
            const obj = parsed as Record<string, unknown>;
            articles = (obj.articles as PubMedArticle[]) ?? (obj.results as PubMedArticle[]) ?? [];
        }

        return <PubMedOutput articles={articles} query={query} />;
    }

    // ── pubmed_fetch ──────────────────────────
    if (toolName === "pubmed_fetch") {
        let article: PubMedArticle | null = null;
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            article = parsed as PubMedArticle;
        } else if (Array.isArray(parsed) && parsed.length > 0) {
            article = (parsed as PubMedArticle[])[0];
        }
        return article ? <PubMedOutput articles={[article]} /> : <RawOutput output={output} />;
    }

    // ── default: raw pre-formatted text ───────
    return <RawOutput output={output} />;
}

function RawOutput({ output }: { output: string }) {
    return (
        <pre className="text-xs font-mono text-[--text-2] bg-[--bg-panel] border border-[--bdr] rounded-lg p-2 overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto scrollbar-thin">
            {output}
        </pre>
    );
}
