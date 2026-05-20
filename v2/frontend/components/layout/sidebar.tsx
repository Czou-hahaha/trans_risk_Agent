"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FileText,
  LayoutDashboard,
  PlusCircle,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/investigation/new", label: "New Investigation", icon: PlusCircle },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
      <div className="flex items-center gap-2 px-5 py-6 border-b border-sidebar-border">
        <Shield className="h-6 w-6 text-blue-400" />
        <div>
          <p className="text-sm font-semibold tracking-tight">Risk Console</p>
          <p className="text-xs text-sidebar-muted">AI Investigation v2</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-white"
                  : "text-sidebar-muted hover:bg-sidebar-accent hover:text-white"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-sidebar-border px-5 py-4 text-xs text-sidebar-muted">
        <div className="flex items-center gap-2">
          <Activity className="h-3.5 w-3.5" />
          Deterministic workflow
        </div>
        <div className="mt-1 flex items-center gap-2">
          <FileText className="h-3.5 w-3.5" />
          monitor → contribution → summary
        </div>
      </div>
    </aside>
  );
}
