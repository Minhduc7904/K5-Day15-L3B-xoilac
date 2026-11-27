import { MascotAnimation } from '@/components/mascot/mascot-animation';

export default function Loading() {
  return (
    <div
      role="status"
      className="grid min-h-[calc(100dvh-4rem)] place-content-center justify-items-center gap-2 px-4 text-sm font-medium"
    >
      <MascotAnimation motion="running" size={144} />
      <p>Đang tải Examind…</p>
    </div>
  );
}
