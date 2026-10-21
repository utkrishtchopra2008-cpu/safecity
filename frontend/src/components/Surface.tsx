import type { ReactNode } from 'react';

type SurfaceProps = {
  children: ReactNode;
  className?: string;
};

export function Surface({ children, className = '' }: SurfaceProps) {
  return <section className={`surface ${className}`.trim()}>{children}</section>;
}
