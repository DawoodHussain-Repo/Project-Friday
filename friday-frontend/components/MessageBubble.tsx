import type { FridayEvent } from "../lib/api";

interface MessageBubbleProps {
  event: FridayEvent;
}

export function MessageBubble({ event }: MessageBubbleProps) {
  if (event.type === "user") {
    return (
      <div className="flex w-full justify-end">
        <div className="max-w-[94%] animate-rise-in rounded-2xl border border-friday-userBorder bg-friday-brandSoft px-4 py-3 text-friday-userText shadow-sm sm:max-w-[82%]">
          {event.content}
        </div>
      </div>
    );
  }

  if (event.type === "tool_call") {
    return (
      <div className="flex w-full justify-start">
        <div className="max-w-[96%] animate-rise-in rounded-2xl border border-dashed border-friday-line bg-friday-soft px-4 py-3 text-sm text-friday-ink sm:max-w-[90%]">
          <div className="mb-2 inline-flex rounded-full border border-friday-pillBorder bg-friday-pillBg px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-friday-pillText">
            Tool call
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-5">
            {event.content}
          </pre>
        </div>
      </div>
    );
  }

  if (event.type === "tool_result") {
    return (
      <div className="flex w-full justify-start">
        <details className="max-w-[96%] animate-rise-in rounded-2xl border border-dashed border-friday-line bg-friday-soft px-4 py-3 text-sm text-friday-ink sm:max-w-[90%]">
          <summary className="mb-2 inline-flex cursor-pointer rounded-full border border-friday-pillBorder bg-friday-pillBg px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-friday-pillText">
            Tool result
          </summary>
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-5">
            {event.content}
          </pre>
        </details>
      </div>
    );
  }

  if (event.type === "thought") {
    return (
      <div className="flex w-full justify-start">
        <div className="max-w-[96%] animate-rise-in rounded-2xl border border-dashed border-friday-line bg-friday-soft px-4 py-3 text-sm text-friday-ink sm:max-w-[90%]">
          <div className="mb-2 inline-flex rounded-full border border-friday-pillBorder bg-friday-pillBg px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-friday-pillText">
            Reasoning step
          </div>
          <div className="whitespace-pre-wrap">{event.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[96%] animate-rise-in whitespace-pre-wrap rounded-2xl border border-friday-line bg-friday-paper px-4 py-3 leading-6 text-friday-ink sm:max-w-[90%]">
        {event.content}
      </div>
    </div>
  );
}
