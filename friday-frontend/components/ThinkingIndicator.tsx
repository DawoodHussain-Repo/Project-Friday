export function ThinkingIndicator() {
  return (
    <div
      className="inline-flex items-center gap-2 rounded-2xl border border-friday-line bg-[#f7f3ea] px-3 py-2 text-sm text-friday-muted"
      aria-live="polite"
    >
      <span className="size-1.5 animate-float-dot rounded-full bg-[#8e8678]" />
      <span className="size-1.5 animate-float-dot rounded-full bg-[#8e8678] [animation-delay:0.15s]" />
      <span className="size-1.5 animate-float-dot rounded-full bg-[#8e8678] [animation-delay:0.3s]" />
      Friday is thinking
    </div>
  );
}
