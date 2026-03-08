"use client";

import {
    useQuery,
    useMutation,
    useQueryClient,
    QueryClient,
    QueryClientProvider,
} from "@tanstack/react-query";
import { getGatewayBaseURL } from "@/core/config";
import type { Thread } from "@/core/models/types";

// ──────────────────────────────────────
// Gateway HTTP client
// ──────────────────────────────────────

async function gatewayFetch<T>(
    path: string,
    options?: RequestInit
): Promise<T> {
    const base = getGatewayBaseURL();
    const res = await fetch(`${base}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options?.headers,
        },
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${res.status}: ${text}`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
}

// ──────────────────────────────────────
// Thread Hooks
// ──────────────────────────────────────

export function useThreads() {
    return useQuery<Thread[]>({
        queryKey: ["threads"],
        queryFn: () => gatewayFetch<Thread[]>("/api/threads"),
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: false,
    });
}

export function useCreateThread() {
    const queryClient = useQueryClient();
    return useMutation<Thread, Error, { title?: string }>({
        mutationFn: ({ title = "New Conversation" }) =>
            gatewayFetch<Thread>("/api/threads", {
                method: "POST",
                body: JSON.stringify({ title }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threads"] });
        },
    });
}

export function useDeleteThread() {
    const queryClient = useQueryClient();
    return useMutation<void, Error, string>({
        mutationFn: (threadId: string) =>
            gatewayFetch<void>(`/api/threads/${threadId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threads"] });
        },
    });
}

// ──────────────────────────────────────
// QueryClient factory
// ──────────────────────────────────────

export function makeQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { staleTime: 60 * 1000 },
        },
    });
}

export { QueryClientProvider };
