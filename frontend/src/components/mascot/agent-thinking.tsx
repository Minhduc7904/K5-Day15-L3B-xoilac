import { MascotAnimation } from './mascot-animation';

export function AgentThinking({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <div role="status" className="flex items-center gap-2 text-sm">
      <MascotAnimation motion="thinking" size={56} />
      <span>Examind đang suy nghĩ…</span>
    </div>
  );
}
