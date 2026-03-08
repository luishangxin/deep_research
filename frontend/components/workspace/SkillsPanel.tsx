"use client";

import { useState, useEffect } from "react";
import { Wrench, ChevronRight, Loader2, AlertCircle, Edit2, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "@/components/workspace/MarkdownRenderer";
import { useSkills, useSkillContent, useSkillRawContent, useUpdateSkill, type Skill } from "@/core/skills/hooks";


export function SkillsPanel() {
    const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState("");

    const { data: skills, isLoading, error } = useSkills();
    const {
        data: skillContent,
        isLoading: isLoadingContent,
    } = useSkillContent(selectedSkill);
    const { data: skillRawContent, isLoading: isLoadingRaw } = useSkillRawContent(isEditing ? selectedSkill : null);
    const updateSkill = useUpdateSkill();

    useEffect(() => {
        if (isEditing && skillRawContent) {
            setEditContent(skillRawContent.content);
        }
    }, [isEditing, skillRawContent]);

    useEffect(() => {
        setIsEditing(false);
    }, [selectedSkill]);

    return (
        <div className="flex h-full overflow-hidden">
            {/* Left: Skill list */}
            <aside className="w-72 shrink-0 flex flex-col border-r border-black/8 dark:border-white/5 bg-[--bg-surface]">
                <div className="px-4 py-4 border-b border-black/8 dark:border-white/5">
                    <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shrink-0 shadow-sm">
                            <Wrench className="w-3.5 h-3.5 text-white" />
                        </div>
                        <h2 className="font-semibold text-sm text-[--text-primary]">Skills</h2>
                    </div>
                    <p className="mt-1 text-xs text-[--text-muted]">Select a skill to view its details</p>
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
                    {isLoading && (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-4 h-4 animate-spin text-[--text-muted]" />
                        </div>
                    )}
                    {error && (
                        <div className="flex items-center gap-2 p-3 text-xs text-red-500">
                            <AlertCircle className="w-4 h-4 shrink-0" />
                            <span>Failed to load skills</span>
                        </div>
                    )}
                    {skills?.map((skill: Skill) => (
                        <SkillListItem
                            key={skill.name}
                            skill={skill}
                            isActive={selectedSkill === skill.name}
                            onClick={() => setSelectedSkill(skill.name)}
                        />
                    ))}
                    {!isLoading && !error && skills?.length === 0 && (
                        <p className="text-xs text-[--text-muted] text-center py-8">No skills found</p>
                    )}
                </div>
            </aside>

            {/* Right: Skill content */}
            <main className="flex-1 overflow-y-auto p-6 bg-[--bg-base]">
                {!selectedSkill ? (
                    <EmptyState />
                ) : isEditing ? (
                    isLoadingRaw ? (
                        <div className="flex items-center justify-center h-32">
                            <Loader2 className="w-5 h-5 animate-spin text-[--text-muted]" />
                        </div>
                    ) : (
                        <div className="max-w-3xl mx-auto h-full flex flex-col">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-lg text-[--text-primary] flex items-center gap-2">
                                    <Edit2 className="w-4 h-4 text-orange-500" />
                                    Editing {selectedSkill}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setIsEditing(false)}
                                        className="px-3 py-1.5 text-sm font-medium text-[--text-secondary] hover:bg-black/5 dark:hover:bg-white/5 rounded-md flex items-center gap-1.5 transition-colors"
                                        disabled={updateSkill.isPending}
                                    >
                                        <X className="w-4 h-4" /> Cancel
                                    </button>
                                    <button
                                        onClick={async () => {
                                            if (!selectedSkill) return;
                                            try {
                                                await updateSkill.mutateAsync({ name: selectedSkill, content: editContent });
                                                setIsEditing(false);
                                            } catch (e) {
                                                console.error("Failed to update skill", e);
                                            }
                                        }}
                                        disabled={updateSkill.isPending}
                                        className="px-3 py-1.5 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-md flex items-center gap-1.5 transition-colors disabled:opacity-50"
                                    >
                                        {updateSkill.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                        Save
                                    </button>
                                </div>
                            </div>
                            {updateSkill.isError && (
                                <div className="mb-4 p-3 rounded-md bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4 shrink-0" />
                                    Failed to save changes.
                                </div>
                            )}
                            <textarea
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                                className="flex-1 w-full p-4 font-mono text-sm bg-black/5 dark:bg-white/5 rounded-lg border border-transparent focus:border-orange-500/50 focus:outline-none resize-none text-[--text-primary]"
                                spellCheck={false}
                            />
                        </div>
                    )
                ) : isLoadingContent ? (
                    <div className="flex items-center justify-center h-32">
                        <Loader2 className="w-5 h-5 animate-spin text-[--text-muted]" />
                    </div>
                ) : skillContent ? (
                    <div className="max-w-3xl mx-auto">
                        <div className="flex justify-end mb-4">
                            <button
                                onClick={() => {
                                    setIsEditing(true);
                                }}
                                className="px-3 py-1.5 text-sm font-medium text-[--text-secondary] hover:text-[--text-primary] hover:bg-black/5 dark:hover:bg-white/5 rounded-md flex items-center gap-1.5 transition-colors"
                            >
                                <Edit2 className="w-4 h-4" />
                                Edit Skill
                            </button>
                        </div>
                        <MarkdownRenderer content={skillContent.content} />
                    </div>
                ) : null}
            </main>
        </div>
    );
}

function SkillListItem({
    skill,
    isActive,
    onClick,
}: {
    skill: Skill;
    isActive: boolean;
    onClick: () => void;
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-all duration-100 group",
                isActive
                    ? "bg-orange-50 dark:bg-orange-500/10 text-[--text-primary]"
                    : "text-[--text-muted] hover:text-[--text-secondary] hover:bg-black/5 dark:hover:bg-white/5"
            )}
        >
            <Wrench
                className={cn(
                    "w-3.5 h-3.5 mt-0.5 shrink-0 transition-colors",
                    isActive ? "text-orange-500" : "text-[--text-muted]"
                )}
            />
            <div className="flex-1 min-w-0">
                <p className={cn("text-xs font-medium truncate", isActive && "text-orange-600 dark:text-orange-400")}>
                    {skill.name}
                </p>
                {skill.description && (
                    <p className="text-[10px] text-[--text-muted] mt-0.5 line-clamp-2 leading-relaxed">
                        {skill.description}
                    </p>
                )}
            </div>
            <ChevronRight
                className={cn(
                    "w-3 h-3 shrink-0 mt-0.5 transition-all",
                    isActive ? "text-orange-400 opacity-100" : "opacity-0 group-hover:opacity-50"
                )}
            />
        </button>
    );
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center h-full text-center py-16 gap-3">
            <div className="w-12 h-12 rounded-xl bg-orange-50 dark:bg-orange-500/10 flex items-center justify-center">
                <Wrench className="w-6 h-6 text-orange-400" />
            </div>
            <div>
                <p className="text-sm font-medium text-[--text-secondary]">Select a skill</p>
                <p className="text-xs text-[--text-muted] mt-1">Choose a skill from the list to view its documentation</p>
            </div>
        </div>
    );
}
