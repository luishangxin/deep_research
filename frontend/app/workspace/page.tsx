"use client";

import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Flame, Zap, Cpu, Rocket, ArrowRight } from "lucide-react";
import { useCreateThread } from "@/core/threads/hooks";

const SUGGESTIONS = [
    "Write a comprehensive research report on quantum computing",
    "Analyze the latest trends in large language models",
    "Help me debug and optimize this Python code",
    "Explain the differences between cloud providers for ML workloads",
];

export default function WorkspacePage() {
    const router = useRouter();
    const createThread = useCreateThread();

    const handleSuggestion = async (suggestion: string) => {
        try {
            const thread = await createThread.mutateAsync({ title: suggestion.slice(0, 50) });
            router.push(`/workspace/chats/${thread.id}?q=${encodeURIComponent(suggestion)}`);
        } catch {
            router.push(`/workspace/chats/new?q=${encodeURIComponent(suggestion)}`);
        }
    };

    const handleNewChat = async () => {
        try {
            const thread = await createThread.mutateAsync({ title: "New Conversation" });
            router.push(`/workspace/chats/${thread.id}`);
        } catch {
            router.push("/workspace/chats/new");
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-full px-4 bg-[--bg-base]">
            {/* Hero */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-center mb-10"
            >
                <div className="flex items-center justify-center mb-4">
                    <div className="relative">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-xl shadow-orange-200 dark:shadow-orange-900/40">
                            <Flame className="w-8 h-8 text-white relative z-10" />
                        </div>
                        <motion.div
                            className="absolute inset-0 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 blur-xl opacity-20"
                            animate={{ scale: [1, 1.15, 1], opacity: [0.2, 0.35, 0.2] }}
                            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
                        />
                    </div>
                </div>
                <h1 className="text-4xl font-bold text-[--text-primary] mb-3 tracking-tight">
                    Flow Agent
                </h1>
                <p className="text-[--text-muted] text-base max-w-md mx-auto leading-relaxed">
                    Multi-agent AI research assistant. Ask anything — from deep research to code execution.
                </p>
            </motion.div>

            {/* Mode pills */}
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="flex items-center gap-2 mb-10"
            >
                {[
                    { icon: Zap, label: "Flash", light: "text-yellow-600 bg-yellow-50 border-yellow-200", dark: "dark:text-yellow-400 dark:bg-yellow-400/10 dark:border-yellow-400/20" },
                    { icon: Cpu, label: "Pro", light: "text-blue-600 bg-blue-50 border-blue-200", dark: "dark:text-blue-400 dark:bg-blue-400/10 dark:border-blue-400/20" },
                    { icon: Rocket, label: "Ultra", light: "text-violet-600 bg-violet-50 border-violet-200", dark: "dark:text-violet-400 dark:bg-violet-400/10 dark:border-violet-400/20" },
                ].map(({ icon: Icon, label, light, dark }) => (
                    <div key={label} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium ${light} ${dark}`}>
                        <Icon className="w-3 h-3" />
                        {label}
                    </div>
                ))}
            </motion.div>

            {/* CTA */}
            <motion.button
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.15 }}
                onClick={handleNewChat}
                className="flex items-center gap-2 px-6 py-3 mb-10 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-medium transition-all shadow-lg shadow-violet-200 dark:shadow-violet-900/40"
            >
                Start New Conversation
                <ArrowRight className="w-4 h-4" />
            </motion.button>

            {/* Suggestion chips */}
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl w-full"
            >
                {SUGGESTIONS.map((s, i) => (
                    <motion.button
                        key={s}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.25 + i * 0.05 }}
                        onClick={() => handleSuggestion(s)}
                        className="px-4 py-3 rounded-xl border border-[--border] bg-[--bg-surface] hover:bg-[--bg-panel] hover:border-black/12 dark:hover:border-white/15 text-sm text-[--text-muted] hover:text-[--text-secondary] text-left transition-all duration-150 shadow-xs"
                    >
                        {s}
                    </motion.button>
                ))}
            </motion.div>
        </div>
    );
}
