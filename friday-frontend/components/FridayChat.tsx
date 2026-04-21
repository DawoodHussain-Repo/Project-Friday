"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { useFridayStream } from "../hooks/useFridayStream";
import { getWorkspaceTree, WorkspaceNode } from "../lib/api";
import { MessageBubble } from "./MessageBubble";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { WorkspacePanel } from "./WorkspacePanel";

export function FridayChat() {
  const { events, send, stop, isStreaming } = useFridayStream();
  const [query, setQuery] = useState("");
  const [tree, setTree] = useState<WorkspaceNode[]>([]);
  const endRef = useRef<HTMLDivElement | null>(null);

  const refreshWorkspace = useCallback(async () => {
    try {
      const snapshot = await getWorkspaceTree();
      setTree(snapshot);
    } catch {
      setTree([]);
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

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isStreaming) {
      return;
    }

    setQuery("");
    await send(trimmed);
  };

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-3 py-4 md:px-5 lg:grid-cols-[minmax(0,2.25fr)_minmax(280px,1fr)] lg:gap-5 lg:py-6">
      <section className="flex min-h-[72vh] flex-col rounded-2xl border border-friday-line bg-friday-paper shadow-panel lg:min-h-[82vh]">
        <header className="border-b border-friday-line px-5 pb-4 pt-6">
          <h1 className="font-heading text-[1.6rem] leading-tight text-friday-ink">
            Project Friday
          </h1>
          <p className="mt-2 text-base text-friday-muted">
            ReAct brain with sandboxed tools and a learning skill library
          </p>
        </header>

        <div className="chat-scrollbar flex flex-1 flex-col gap-4 overflow-auto px-4 py-5">
          {events.map((event, index) => (
            <MessageBubble key={`${event.type}-${index}`} event={event} />
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
            className="flex-1 rounded-xl border border-[#d7ceb9] bg-[#fffcf6] px-3 py-2.5 text-base text-friday-ink outline-none transition focus:border-[#95b4d4] focus:ring-2 focus:ring-[#d8e5f2]"
            placeholder="Ask Friday anything"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          {isStreaming ? (
            <button
              className="min-w-24 rounded-xl border border-[#c89f9f] bg-[#f6e9e8] px-4 py-2.5 text-sm font-semibold text-[#8a3530] transition hover:bg-[#f1dfdd]"
              type="button"
              onClick={stop}
            >
              Stop
            </button>
          ) : null}

          <button
            className="min-w-24 rounded-xl bg-friday-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isStreaming}
          >
            Send
          </button>
        </form>
      </section>

      <WorkspacePanel nodes={tree} />
    </main>
  );
}
