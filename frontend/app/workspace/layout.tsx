"use client";

import { useState } from "react";
import { Sidebar } from "@/components/workspace/Sidebar";

export default function WorkspaceLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div className="flex h-full w-full overflow-hidden bg-[--bg-base]">
            <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
            <main className="flex-1 flex flex-col overflow-hidden relative">
                {children}
            </main>
        </div>
    );
}
