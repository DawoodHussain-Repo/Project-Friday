"use client";

import { useCallback, useEffect, useState } from "react";

import type { FridayEvent } from "../lib/api";

interface SkillInfo {
  name: string;
  context_preview: string;
}

export function SkillsPanel() {
  const [skills, setSkills] = useState<
    { name: string; description: string; path: string }[]
  >([]);
  const [agents, setAgents] = useState<SkillInfo[]>([]);
  const [tab, setTab] = useState<"skills" | "agents">("agents");

  const refresh = useCallback(async () => {
    try {
      const [skillsRes, agentsRes] = await Promise.all([
        fetch("/api/friday/skills"),
        fetch("/api/friday/agents"),
      ]);
      if (skillsRes.ok) {
        const data = await skillsRes.json();
        setSkills(data.skills ?? []);
      }
      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgents(data.agents ?? []);
      }
    } catch {
      /* silently ignore fetch errors */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 10_000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <aside className="chat-scrollbar min-h-[32vh] overflow-auto rounded-2xl border border-friday-line bg-friday-paper p-4 shadow-panel lg:min-h-[82vh]">
      <div className="mb-3 flex items-center gap-2">
        <button
          className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${tab === "agents" ? "bg-friday-brand text-white" : "bg-friday-soft text-friday-muted hover:bg-friday-line"}`}
          onClick={() => setTab("agents")}
        >
          Skill Agents
        </button>
        <button
          className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${tab === "skills" ? "bg-friday-brand text-white" : "bg-friday-soft text-friday-muted hover:bg-friday-line"}`}
          onClick={() => setTab("skills")}
        >
          Scripts
        </button>
        <button
          className="ml-auto rounded-lg bg-friday-soft px-2 py-1 text-[10px] font-semibold text-friday-muted transition hover:bg-friday-line"
          onClick={refresh}
          title="Refresh"
        >
          ↻
        </button>
      </div>

      {tab === "agents" ? (
        agents.length === 0 ? (
          <p className="text-sm text-friday-muted">
            No skill agents yet. Ask Friday to create one!
          </p>
        ) : (
          <ul className="space-y-2">
            {agents.map((a) => (
              <li
                key={a.name}
                className="rounded-xl border border-friday-line bg-friday-soft p-3"
              >
                <p className="text-sm font-semibold text-friday-ink">
                  {a.name}
                </p>
                <p className="mt-1 line-clamp-3 text-xs text-friday-muted">
                  {a.context_preview}
                </p>
              </li>
            ))}
          </ul>
        )
      ) : skills.length === 0 ? (
        <p className="text-sm text-friday-muted">
          No committed skill scripts yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {skills.map((s) => (
            <li
              key={s.name}
              className="rounded-xl border border-friday-line bg-friday-soft p-3"
            >
              <p className="text-sm font-semibold text-friday-ink">{s.name}</p>
              <p className="mt-1 text-xs text-friday-muted">{s.description}</p>
              <p className="mt-0.5 truncate font-mono text-[10px] text-friday-muted">
                {s.path}
              </p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
