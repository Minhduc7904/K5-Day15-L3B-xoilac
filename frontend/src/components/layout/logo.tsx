import Image from 'next/image';
import Link from 'next/link';
import { cn } from '@/lib/cn';

interface LogoProps {
  /** `full`: biểu tượng + chữ. `mark`: chỉ biểu tượng vuông. */
  variant?: 'full' | 'mark';
  href?: string;
  className?: string;
  priority?: boolean;
}

export function Logo({ variant = 'full', href = '/', className, priority }: LogoProps) {
  const image =
    variant === 'full' ? (
      <Image
        src="/brand/examind-logo.webp"
        alt="Examind"
        width={972}
        height={285}
        sizes="168px"
        className={cn('h-auto w-[132px] sm:w-[152px]', className)}
        preload={priority}
      />
    ) : (
      <Image
        src="/brand/examind-mark.png"
        alt="Examind"
        width={512}
        height={512}
        sizes="48px"
        className={cn('size-10', className)}
        preload={priority}
      />
    );

  return (
    <Link
      href={href}
      className="inline-flex shrink-0 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
    >
      {image}
    </Link>
  );
}
