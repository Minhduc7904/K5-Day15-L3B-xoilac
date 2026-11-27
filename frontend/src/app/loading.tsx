import { MascotAnimation } from '@/components/mascot/mascot-animation';

export default function Loading() {
  return (
    <div
      role="status"
      className="grid min-h-dvh place-content-center justify-items-center gap-3 px-4 text-label text-muted-foreground"
    >
      <MascotAnimation motion="running" size={144} />
      <p>Đang tải Examind…</p>
    </div>
  );
}
