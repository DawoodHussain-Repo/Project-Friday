"use client";

import { useCallback, useRef, useState } from "react";

import type { FridayEvent } from "../lib/api";

export interface StreamEvent extends FridayEvent {
  id: string;
}

function createConversationId(): string {
  return crypto.randomUUID();
}

function parseSsePayload(raw: string): FridayEvent[] {
  const events: FridayEvent[] = [];
  const blocks = raw.split("\n\n");

  for (const block of blocks) {
    const lines = block.split("\n").filter((line) => line.startsWith("data:"));
    for (const line of lines) {
      const payload = line.slice(5).trim();
      if (!payload) {
        continue;
      }

      try {
        const parsed = JSON.parse(payload) as FridayEvent;
        events.push(parsed);
      } catch {
        if (process.env.NODE_ENV !== "production") {
          console.warn("Ignoring malformed SSE payload", payload);
        }
      }
    }
  }

  return events;
}

function appendUniqueEvents(
  existing: StreamEvent[],
  incoming: FridayEvent[],
  allocateId: () => string,
): StreamEvent[] {
  const next = [...existing];

  for (const event of incoming) {
    const content = event.content?.trim();
    if (!content) {
      continue;
    }

    const normalized: FridayEvent = { ...event, content };
    const last = next[next.length - 1];

    const recentlySeen = next
      .slice(Math.max(next.length - 8, 0))
      .some(
        (item) =>
          item.type === normalized.type && item.content === normalized.content,
      );

    if (
      last &&
      last.type === normalized.type &&
      last.content === normalized.content
    ) {
      continue;
    }

    if (
      recentlySeen &&
      (normalized.type === "final" || normalized.type === "thought")
    ) {
      continue;
    }

    // Convert duplicate thought/final pairs into a single final message.
    if (
      normalized.type === "final" &&
      last &&
      last.type === "thought" &&
      last.content === normalized.content
    ) {
      next[next.length - 1] = { ...normalized, id: last.id };
      continue;
    }

    next.push({ ...normalized, id: allocateId() });
  }

  return next;
}

export function useFridayStream() {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [controller, setController] = useState<AbortController | null>(null);
  const [conversationId] = useState(createConversationId);
  const nextEventCounter = useRef(0);

  const allocateEventId = useCallback(() => {
    nextEventCounter.current += 1;
    return `evt-${nextEventCounter.current}`;
  }, []);

  const send = useCallback(
    async (query: string) => {
      if (isStreaming) {
        return;
      }

      setIsStreaming(true);
      const abortController = new AbortController();
      setController(abortController);

      setEvents((prev) =>
        appendUniqueEvents(
          prev,
          [{ type: "user", content: query }],
          allocateEventId,
        ),
      );

      try {
        const response = await fetch("/api/friday", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, conversation_id: conversationId }),
          signal: abortController.signal,
        });

        if (!response.ok || !response.body) {
          const details = await response.text();
          throw new Error(details || "Failed to start stream");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() ?? "";

          for (const chunk of chunks) {
            const parsed = parseSsePayload(chunk + "\n\n");
            if (parsed.length > 0) {
              setEvents((prev) =>
                appendUniqueEvents(prev, parsed, allocateEventId),
              );
            }
          }
        }

        if (buffer.trim()) {
          const parsed = parseSsePayload(buffer);
          if (parsed.length > 0) {
            setEvents((prev) =>
              appendUniqueEvents(prev, parsed, allocateEventId),
            );
          }
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          setEvents((prev) =>
            appendUniqueEvents(
              prev,
              [{ type: "final", content: "Stopped by user." }],
              allocateEventId,
            ),
          );
          return;
        }

        const message =
          error instanceof Error ? error.message : "Unknown stream error";
        setEvents((prev) =>
          appendUniqueEvents(
            prev,
            [{ type: "final", content: `Error: ${message}` }],
            allocateEventId,
          ),
        );
      } finally {
        setController(null);
        setIsStreaming(false);
      }
    },
    [allocateEventId, conversationId, isStreaming],
  );

  const stop = useCallback(() => {
    if (!controller) {
      return;
    }
    controller.abort();
  }, [controller]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    nextEventCounter.current = 0;
  }, []);

  return { events, send, stop, isStreaming, clearEvents };
}
