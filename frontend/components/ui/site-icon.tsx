type IconName =
  | 'arrow'
  | 'bookmark'
  | 'code'
  | 'document'
  | 'external'
  | 'github'
  | 'search'
  | 'share'
  | 'sparkle';

type SiteIconProps = {
  name: IconName;
  className?: string;
};

/** Small, dependency-free SVG icons used in the public interface. */
export function SiteIcon({ name, className = 'size-4' }: SiteIconProps) {
  const common = {
    className,
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    strokeWidth: 1.8,
    viewBox: '0 0 24 24',
    'aria-hidden': true,
  };

  if (name === 'arrow') return <svg {...common}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
  if (name === 'search') return <svg {...common}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>;
  if (name === 'bookmark') return <svg {...common}><path d="M6 4.8A1.8 1.8 0 0 1 7.8 3h8.4A1.8 1.8 0 0 1 18 4.8V21l-6-4-6 4Z" /></svg>;
  if (name === 'document') return <svg {...common}><path d="M6 2.8h8l4 4V21H6Z" /><path d="M14 3v5h4M9 12h6M9 16h6" /></svg>;
  if (name === 'external') return <svg {...common}><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></svg>;
  if (name === 'share') return <svg {...common}><circle cx="18" cy="5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="19" r="2.5" /><path d="m8.2 10.8 7.5-4.4M8.2 13.2l7.5 4.4" /></svg>;
  if (name === 'sparkle') return <svg {...common}><path d="m12 2 1.4 4.6L18 8l-4.6 1.4L12 14l-1.4-4.6L6 8l4.6-1.4ZM18.5 14l.8 2.7L22 17.5l-2.7.8-.8 2.7-.8-2.7-2.7-.8 2.7-.8Z" /></svg>;
  if (name === 'code') return <svg {...common}><path d="m8 9-3 3 3 3M16 9l3 3-3 3M14 5l-4 14" /></svg>;
  return <svg {...common}><path d="M9 19c-4 1.2-4-2-5-2.5M14 22v-3.1c0-.9.3-1.6.8-2-2.7-.3-5.5-1.3-5.5-6A4.7 4.7 0 0 1 10.6 7c-.1-.3-.6-1.7.1-3.4 0 0 1.1-.3 3.5 1.3a12 12 0 0 1 6.3 0C23 3.3 24 3.6 24 3.6c.7 1.7.2 3.1.1 3.4a4.7 4.7 0 0 1 1.3 3.3c0 4.7-2.8 5.7-5.5 6 .5.4.8 1.3.8 2.5V22" transform="translate(-3)" /></svg>;
}
