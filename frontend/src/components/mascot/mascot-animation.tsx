import Image from 'next/image';

type MascotMotion = 'running' | 'thinking';

interface MascotAnimationProps {
  motion: MascotMotion;
  size: number;
}

export function MascotAnimation({ motion, size }: MascotAnimationProps) {
  const assetPath = `/brand/mascot/${motion}`;

  return (
    <picture>
      <source media="(prefers-reduced-motion: reduce)" srcSet={`${assetPath}/frame-01.webp`} />
      <Image
        src={`${assetPath}/loop.webp`}
        alt=""
        width={size}
        height={size}
        loading="eager"
        unoptimized
      />
    </picture>
  );
}
