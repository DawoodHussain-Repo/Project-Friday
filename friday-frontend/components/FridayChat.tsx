"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { useFridayStream } from "../hooks/useFridayStream";
import { getWorkspaceTree, WorkspaceNode } from "../lib/api";
import { MessageBubble } from "./MessageBubble";
import { SkillsPanel } from "./SkillsPanel";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { WorkspacePanel } from "./WorkspacePanel";

export function FridayChat() {
  const { events, send, stop, isStreaming, clearEvents } = useFridayStream();
  const [query, setQuery] = useState("");
  const [tree, setTree] = useState<WorkspaceNode[]>([]);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<"workspace" | "skills">(
    "workspace",
  );
  const endRef = useRef<HTMLDivElement | null>(null);

  const refreshWorkspace = useCallback(async () => {
    setWorkspaceLoading(true);
    try {
      const snapshot = await getWorkspaceTree();
      setTree(snapshot);
    } catch {
      setTree([]);
    } finally {
      setWorkspaceLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    const last = events[events.length - 1];
    if (last?.type === "tool_result") {
      void refreshWorkspace();
    }
  }, [events, refreshWorkspace]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events, isStreaming]);

  const onSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (!trimmed || isStreaming) {
        return;
      }

      setQuery("");
      await send(trimmed);
    },
    [isStreaming, query, send],
  );

  const onNewChat = () => {
    if (isStreaming) {
      stop();
    }
    clearEvents();
  };

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-3 py-4 md:px-5 lg:grid-cols-[minmax(0,2.25fr)_minmax(280px,1fr)] lg:gap-5 lg:py-6">
      <section className="flex min-h-[72vh] flex-col rounded-2xl border border-friday-line bg-friday-paper shadow-panel lg:min-h-[82vh]">
        <header className="flex items-start justify-between border-b border-friday-line px-5 pb-4 pt-6">
          <div>
            <h1 className="font-heading text-[1.6rem] leading-tight text-friday-ink">
              Project Friday
            </h1>
            <p className="mt-2 text-base text-friday-muted">
              ReAct brain · sandboxed tools · self-improving skill library
            </p>
          </div>
          <button
            className="mt-1 rounded-xl border border-friday-line bg-friday-soft px-3 py-1.5 text-xs font-semibold text-friday-muted transition hover:border-friday-alertBorder hover:bg-friday-alertBg hover:text-friday-alertText"
            onClick={onNewChat}
            title="Start a new conversation"
          >
            New Chat
          </button>
        </header>

        <div className="chat-scrollbar flex flex-1 flex-col gap-4 overflow-auto px-4 py-5">
          {events.length === 0 ? (
            <div className="m-auto text-center text-friday-muted">
              <p className="text-lg font-heading">Good day.</p>
              <p className="mt-1 text-sm">
                Ask me to build something, research a topic, or create a skill
                agent.
              </p>
            </div>
          ) : null}
          {events.map((event) => (
            <MessageBubble key={event.id} event={event} />
          ))}
          {isStreaming ? (
            <div className="flex w-full justify-start">
              <ThinkingIndicator />
            </div>
          ) : null}
          <div ref={endRef} />
        </div>

        <form
          className="flex gap-2 rounded-b-2xl border-t border-friday-line bg-friday-paper p-3"
          onSubmit={onSubmit}
        >
          <input
            id="friday-chat-input"
            className="flex-1 rounded-xl border border-friday-inputBorder bg-friday-inputBg px-3 py-2.5 text-base text-friday-ink outline-none transition focus:border-friday-focusBorder focus:ring-2 focus:ring-friday-focusRing"
            placeholder="Ask Friday anything…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          {isStreaming ? (
            <button
              className="min-w-24 rounded-xl border border-friday-alertBorder bg-friday-alertBg px-4 py-2.5 text-sm font-semibold text-friday-alertText transition hover:bg-friday-alertBgHover"
              type="button"
              onClick={stop}
            >
              Stop
            </button>
          ) : null}

          <button
            id="friday-send-button"
            className="min-w-24 rounded-xl bg-friday-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isStreaming}
          >
            Send
          </button>
        </form>
      </section>

      {/* Sidebar */}
      <div className="flex flex-col gap-3">
        <div className="flex gap-1 rounded-xl border border-friday-line bg-friday-soft p-1">
          <button
            className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition ${sidebarTab === "workspace" ? "bg-friday-paper text-friday-ink shadow-sm" : "text-friday-muted hover:text-friday-ink"}`}
            onClick={() => setSidebarTab("workspace")}
          >
            Workspace
          </button>
          <button
            className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition ${sidebarTab === "skills" ? "bg-friday-paper text-friday-ink shadow-sm" : "text-friday-muted hover:text-friday-ink"}`}
            onClick={() => setSidebarTab("skills")}
          >
            Skills
          </button>
        </div>

        {sidebarTab === "workspace" ? (
          <WorkspacePanel nodes={tree} isLoading={workspaceLoading} />
        ) : (
          <SkillsPanel />
        )}
      </div>
    </main>
  );
}
