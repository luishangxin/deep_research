"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ExternalLink, ChevronDown, BookOpen, Users, CalendarDays, FlaskConical } from "lucide-react";

// ──────────────────────────────────────
// Types (PubMed E-utilities format)
// ──────────────────────────────────────

export interface PubMedArticle {
    pmid?: string;
    title?: string;
    authors?: string[];
    abstract?: string;
    publication_date?: string;
    journal?: string;
    doi?: string;
    pmc_id?: string;
}

// ──────────────────────────────────────
// Helpers
// ──────────────────────────────────────

function formatAuthors(authors: string[] = []): string {
    if (authors.length === 0) return "";
    if (authors.length <= 3) return authors.join(", ");
    return `${authors.slice(0, 3).join(", ")} +${authors.length - 3} more`;
}

function pubmedUrl(pmid?: string): string {
    return pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : "#";
}

function doiUrl(doi?: string): string {
    return doi ? `https://doi.org/${doi}` : "";
}

// ──────────────────────────────────────
// Single article card
// ──────────────────────────────────────

function PubMedArticleCard({ article, index }: { article: PubMedArticle; index: number }) {
    const [expanded, setExpanded] = useState(false);

    const hasAbstract = !!article.abstract;
    const previewAbstract = article.abstract?.slice(0, 200).trim();
    const isLong = (article.abstract?.length ?? 0) > 200;

    return (
        <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
            className="rounded-xl border border-[--bdr] bg-[--bg-surface] overflow-hidden"
        >
            {/* Card header */}
            <div className="px-3 pt-3 pb-2">
                {/* Badge row */}
                <div className="flex items-center gap-2 mb-1.5">
                    <span className="flex items-center gap-1 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-400 uppercase tracking-wide">
                        <FlaskConical className="w-2.5 h-2.5" />
                        PubMed
                    </span>
                    {article.pmid && (
                        <span className="text-[9px] text-[--text-3] font-mono">PMID: {article.pmid}</span>
                    )}
                    {article.publication_date && (
                        <span className="flex items-center gap-0.5 text-[9px] text-[--text-3] ml-auto">
                            <CalendarDays className="w-2.5 h-2.5" />
                            {article.publication_date}
                        </span>
                    )}
                </div>

                {/* Title */}
                <a
                    href={pubmedUrl(article.pmid)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs font-semibold text-[--text-1] hover:text-green-600 dark:hover:text-green-400 leading-snug transition-colors mb-1.5 no-underline"
                >
                    {article.title ?? "Untitled"}
                </a>

                {/* Journal + authors */}
                {article.journal && (
                    <div className="flex items-center gap-1 mb-1">
                        <BookOpen className="w-2.5 h-2.5 text-[--text-3] shrink-0" />
                        <span className="text-[10px] text-[--text-2] italic truncate">{article.journal}</span>
                    </div>
                )}
                {article.authors && article.authors.length > 0 && (
                    <div className="flex items-center gap-1">
                        <Users className="w-2.5 h-2.5 text-[--text-3] shrink-0" />
                        <span className="text-[10px] text-[--text-3] truncate">{formatAuthors(article.authors)}</span>
                    </div>
                )}
            </div>

            {/* Abstract section */}
            {hasAbstract && (
                <>
                    <div className="border-t border-[--bdr] px-3 py-2">
                        <p className="text-[11px] text-[--text-3] leading-relaxed">
                            {expanded ? article.abstract : `${previewAbstract}${isLong ? "…" : ""}`}
                        </p>
                        {isLong && (
                            <button
                                onClick={() => setExpanded((o) => !o)}
                                className="flex items-center gap-1 mt-1 text-[10px] text-green-600 dark:text-green-400 hover:text-green-500 transition-colors"
                            >
                                {expanded ? "Show less" : "Read abstract"}
                                <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
                            </button>
                        )}
                    </div>
                </>
            )}

            {/* Footer links */}
            <div className="flex items-center gap-3 px-3 py-2 border-t border-[--bdr] bg-[--bg-panel]">
                {article.pmid && (
                    <a
                        href={pubmedUrl(article.pmid)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400 hover:text-green-500 no-underline"
                    >
                        <ExternalLink className="w-2.5 h-2.5" /> PubMed
                    </a>
                )}
                {article.doi && (
                    <a
                        href={doiUrl(article.doi)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[10px] text-[--text-3] hover:text-[--text-2] no-underline"
                    >
                        <ExternalLink className="w-2.5 h-2.5" /> DOI
                    </a>
                )}
                {article.pmc_id && (
                    <a
                        href={`https://www.ncbi.nlm.nih.gov/pmc/articles/${article.pmc_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[10px] text-[--text-3] hover:text-[--text-2] no-underline"
                    >
                        <ExternalLink className="w-2.5 h-2.5" /> PMC
                    </a>
                )}
            </div>
        </motion.div>
    );
}

// ──────────────────────────────────────
// Main component
// ──────────────────────────────────────

interface PubMedOutputProps {
    articles: PubMedArticle[];
    query?: string;
}

export function PubMedOutput({ articles, query }: PubMedOutputProps) {
    if (!articles || articles.length === 0) return null;

    return (
        <div className="mt-2 mb-1">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <FlaskConical className="w-3.5 h-3.5 text-green-500" />
                <span className="text-xs font-medium text-[--text-2]">
                    {articles.length} PubMed article{articles.length > 1 ? "s" : ""}
                    {query && <span className="text-[--text-3] font-normal"> for "{query}"</span>}
                </span>
            </div>

            <div className="space-y-2">
                {articles.map((a, i) => (
                    <PubMedArticleCard key={a.pmid ?? i} article={a} index={i} />
                ))}
            </div>
        </div>
    );
}
