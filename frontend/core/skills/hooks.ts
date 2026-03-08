"use client";

import { useQuery } from "@tanstack/react-query";
import { getGatewayBaseURL } from "@/core/config";

// -------------------------------------------------------------------------- //
// Types
// -------------------------------------------------------------------------- //

export interface Skill {
    name: string;
    description: string;
}

export interface SkillContent {
    name: string;
    content: string;
}

// -------------------------------------------------------------------------- //
// HTTP helper (reuses the same pattern as threads/hooks.ts)
// -------------------------------------------------------------------------- //

async function gatewayFetch<T>(path: string): Promise<T> {
    const base = getGatewayBaseURL();
    const res = await fetch(`${base}${path}`, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return res.json();
}

// -------------------------------------------------------------------------- //
// Hooks
// -------------------------------------------------------------------------- //

export function useSkills() {
    return useQuery<Skill[]>({
        queryKey: ["skills"],
        queryFn: () => gatewayFetch<Skill[]>("/api/skills"),
        staleTime: 60_000,
        retry: false,
    });
}

export function useSkillContent(name: string | null) {
    return useQuery<SkillContent>({
        queryKey: ["skills", name, "content"],
        queryFn: () => gatewayFetch<SkillContent>(`/api/skills/${encodeURIComponent(name!)}/content`),
        enabled: !!name,
        staleTime: 60_000,
        retry: false,
    });
}
