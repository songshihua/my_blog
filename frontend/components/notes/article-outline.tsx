import type { ArticleOutlineItem } from '@/lib/site-data';

export function ArticleOutline({
  items,
  title,
}: {
  items: ArticleOutlineItem[];
  title: string;
}) {
  const visible = items.filter(
    (item, index) =>
      !(index === 0 && item.level === 1 && item.text.trim() === title.trim()),
  );
  return (
    <nav aria-label="本文目录" className="note-outline-nav">
      <h2>本文目录</h2>
      {visible.length ? (
        visible.map((item, index) => (
          <a
            className={index === 0 ? 'active' : ''}
            href={`#${item.id}`}
            key={`${item.id}-${index}`}
            style={{
              paddingLeft: `${12 + Math.max(0, item.level - 2) * 14}px`,
            }}
          >
            {item.text}
          </a>
        ))
      ) : (
        <p>该笔记暂时没有分节标题。</p>
      )}
    </nav>
  );
}
