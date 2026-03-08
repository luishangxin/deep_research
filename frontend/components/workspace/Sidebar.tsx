"use client";

import { useParams, useRouter, usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { motion, AnimatePresence } from "motion/react";
import {
    Plus, Trash2, MessageSquare,
    Sun, Moon, Flame, Loader2, PanelLeftClose, PanelLeftOpen, Wrench,
} from "lucide-react";
import { useState, useEffect } from "react";
import { cn, formatDate, truncate } from "@/lib/utils";
import { useThreads, useCreateThread, useDeleteThread } from "@/core/threads/hooks";
import type { Thread } from "@/core/models/types";

interface SidebarProps {
    collapsed: boolean;
    onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
    const router = useRouter();
    const params = useParams();
    const activeThreadId = params?.thread_id as string | undefined;

    const { theme, setTheme } = useTheme();
    const { data: threads, isLoading } = useThreads();
    const createThread = useCreateThread();
    const deleteThread = useDeleteThread();
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [mounted, setMounted] = useState(false);
    const pathname = usePathname();
    const isSkillsActive = pathname?.startsWith("/workspace/skills");
    useEffect(() => { setMounted(true); }, []);

    const handleNewChat = async () => {
        try {
            const thread = await createThread.mutateAsync({ title: "New Conversation" });
            router.push(`/workspace/chats/${thread.id}`);
        } catch {
            router.push("/workspace/chats/new");
        }
    };

    const handleDelete = async (e: React.MouseEvent, threadId: string) => {
        e.stopPropagation();
        e.preventDefault();
        setDeletingId(threadId);
        try {
            await deleteThread.mutateAsync(threadId);
            if (activeThreadId === threadId) router.push("/workspace");
        } finally {
            setDeletingId(null);
        }
    };

    return (
        <motion.aside
            animate={{ width: collapsed ? 64 : 260 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="relative flex flex-col h-full border-r border-black/8 dark:border-white/5 bg-[--bg-surface] overflow-hidden shrink-0"
        >
            {/* Header */}
            <div className="flex items-center h-14 px-2 gap-1 overflow-hidden">
                {/* Toggle button — always visible, always left-aligned */}
                <button
                    onClick={onToggle}
                    className="p-2 rounded-lg hover:bg-black/8 dark:hover:bg-white/10 text-[--text-muted] hover:text-[--text-primary] transition-colors shrink-0"
                    title={collapsed ? "Open sidebar" : "Close sidebar"}
                >
                    {collapsed
                        ? <PanelLeftOpen className="w-4 h-4" />
                        : <PanelLeftClose className="w-4 h-4" />}
                </button>

                {/* Logo + name — only visible when expanded */}
                {!collapsed && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex items-center gap-2 min-w-0 flex-1 pl-1"
                    >
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shrink-0 shadow-sm">
                            <Flame className="w-3.5 h-3.5 text-white" />
                        </div>
                        <span className="font-semibold text-sm truncate text-[--text-primary]">
                            Flow
                        </span>
                    </motion.div>
                )}
            </div>

            {/* Skills Button */}
            <div className={cn("px-3 pt-3 pb-1", collapsed && "px-2")}>
                <button
                    onClick={() => router.push("/workspace/skills")}
                    className={cn(
                        "group w-full flex items-center gap-2.5 h-9 rounded-lg",
                        isSkillsActive
                            ? "bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 text-violet-600 dark:text-violet-400"
                            : "bg-transparent hover:bg-black/5 dark:hover:bg-white/5 border border-transparent hover:border-black/10 dark:hover:border-white/10 text-[--text-secondary] hover:text-[--text-primary]",
                        "transition-all duration-150 text-sm font-medium",
                        collapsed ? "justify-center px-0" : "px-3"
                    )}
                    title="Skills"
                >
                    <Wrench className={cn("w-4 h-4 shrink-0", isSkillsActive && "text-violet-500")} />
                    {!collapsed && <span>Skills</span>}
                </button>
            </div>

            {/* New Chat Button */}
            <div className={cn("px-3 pb-3 pt-1", collapsed && "px-2")}>
                <button
                    onClick={handleNewChat}
                    disabled={createThread.isPending}
                    className={cn(
                        "group w-full flex items-center gap-2.5 h-9 rounded-lg",
                        "bg-black/5 hover:bg-black/8 dark:bg-white/5 dark:hover:bg-white/10",
                        "border border-black/8 hover:border-black/12 dark:border-white/10 dark:hover:border-white/20",
                        "transition-all duration-150 text-sm font-medium text-[--text-secondary] hover:text-[--text-primary]",
                        collapsed ? "justify-center px-0" : "px-3"
                    )}
                >
                    {createThread.isPending
                        ? <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                        : <Plus className="w-4 h-4 shrink-0" />}
                    {!collapsed && <span>New Chat</span>}
                </button>
            </div>

            {/* Thread List */}
            <div className="flex-1 overflow-y-auto px-2 space-y-0.5 scrollbar-thin">
                {isLoading && !collapsed && (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-4 h-4 animate-spin text-[--text-muted]" />
                    </div>
                )}
                <AnimatePresence>
                    {threads?.map((thread: Thread) => (
                        <motion.div
                            key={thread.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            transition={{ duration: 0.15 }}
                        >
                            <ThreadItem
                                thread={thread}
                                isActive={thread.id === activeThreadId}
                                collapsed={collapsed}
                                isDeleting={deletingId === thread.id}
                                onDelete={handleDelete}
                                onClick={() => router.push(`/workspace/chats/${thread.id}`)}
                            />
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div className={cn(
                "border-t border-black/8 dark:border-white/5 p-2 flex items-center gap-2",
                collapsed && "justify-center flex-col"
            )}>
                <button
                    onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                    className="p-2 rounded-lg hover:bg-black/8 dark:hover:bg-white/10 text-[--text-muted] hover:text-[--text-primary] transition-colors"
                    title="Toggle theme"
                >
                    {mounted && (theme === "dark"
                        ? <Sun className="w-4 h-4" />
                        : <Moon className="w-4 h-4" />)}
                </button>
                {!collapsed && <span className="text-xs text-[--text-muted] ml-auto">v0.1.0</span>}
            </div>


        </motion.aside>
    );
}

function ThreadItem({
    thread, isActive, collapsed, isDeleting, onDelete, onClick,
}: {
    thread: Thread;
    isActive: boolean;
    collapsed: boolean;
    isDeleting: boolean;
    onDelete: (e: React.MouseEvent, id: string) => void;
    onClick: () => void;
}) {
    const [hovered, setHovered] = useState(false);

    return (
        <button
            onClick={onClick}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            className={cn(
                "group w-full flex items-center gap-2.5 h-8 rounded-lg px-2 text-left transition-all duration-100",
                isActive
                    ? "bg-black/8 dark:bg-white/10 text-[--text-primary]"
                    : "text-[--text-muted] hover:text-[--text-secondary] hover:bg-black/5 dark:hover:bg-white/5",
                collapsed && "justify-center px-0"
            )}
        >
            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
            {!collapsed && (
                <>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs truncate">{truncate(thread.title, 28)}</p>
                        <p className="text-[10px] text-[--text-muted]">{formatDate(thread.updated_at)}</p>
                    </div>
                    {hovered && !isDeleting && (
                        <button
                            onClick={(e) => onDelete(e, thread.id)}
                            className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-500/20 text-[--text-muted] hover:text-red-500 dark:hover:text-red-400 transition-colors"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    )}
                    {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin text-[--text-muted]" />}
                </>
            )}
        </button>
    );
}
