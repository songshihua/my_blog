import type { ReactNode } from 'react';
import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type { ArticleOutlineItem } from '@/lib/site-data';

type MarkdownNode = {
  type: string;
  value?: string;
  children?: MarkdownNode[];
  data?: {
    hName?: string;
    hProperties?: Record<string, string>;
  };
};

const HIGHLIGHT_PATTERN =
  /==(?:(yellow|green|blue|purple|pink)\|)?(.+?)==/g;

function remarkHighlights() {
  return (tree: MarkdownNode) => {
    function transform(parent: MarkdownNode) {
      if (!parent.children) return;
      parent.children = parent.children.flatMap((child) => {
        if (child.type !== 'text' || !child.value?.includes('==')) {
          transform(child);
          return [child];
        }

        const nodes: MarkdownNode[] = [];
        let cursor = 0;
        for (const match of child.value.matchAll(HIGHLIGHT_PATTERN)) {
          const index = match.index ?? 0;
          if (index > cursor) {
            nodes.push({ type: 'text', value: child.value.slice(cursor, index) });
          }
          nodes.push({
            type: 'noteHighlight',
            data: {
              hName: 'mark',
              hProperties: {
                'data-highlight': match[1] || 'yellow',
              },
            },
            children: [{ type: 'text', value: match[2] }],
          });
          cursor = index + match[0].length;
        }
        if (cursor === 0) return [child];
        if (cursor < child.value.length) {
          nodes.push({ type: 'text', value: child.value.slice(cursor) });
        }
        return nodes;
      });
    }

    transform(tree);
  };
}

function nodeText(value: ReactNode): string {
  if (typeof value === 'string' || typeof value === 'number')
    return String(value);
  if (Array.isArray(value)) return value.map(nodeText).join('');
  if (value && typeof value === 'object' && 'props' in value) {
    return nodeText(
      (value as { props: { children?: ReactNode } }).props.children,
    );
  }
  return '';
}

export function NoteDocument({
  markdown,
  outline,
  title,
}: {
  markdown: string;
  outline: ArticleOutlineItem[];
  title: string;
}) {
  let headingIndex = 0;
  const makeHeading = (level: 1 | 2 | 3 | 4 | 5 | 6) => {
    function Heading({ children }: { children?: ReactNode }) {
      const item = outline[headingIndex++];
      const Tag = `h${level}` as 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
      if (level === 1 && nodeText(children).trim() === title.trim()) {
        return <span aria-hidden="true" id={item?.id} />;
      }
      return <Tag id={item?.id}>{children}</Tag>;
    }
    return Heading;
  };
  const components: Components = {
    h1: makeHeading(1),
    h2: makeHeading(2),
    h3: makeHeading(3),
    h4: makeHeading(4),
    h5: makeHeading(5),
    h6: makeHeading(6),
    a({ href, children }) {
      if (
        !href ||
        (!href.startsWith('#') &&
          !href.startsWith('/') &&
          !/^https?:\/\//i.test(href))
      ) {
        return <span>{children}</span>;
      }
      const external = /^https?:\/\//i.test(href);
      return (
        <a
          href={href}
          rel={external ? 'noreferrer noopener' : undefined}
          target={external ? '_blank' : undefined}
        >
          {children}
        </a>
      );
    },
    img({ src, alt }) {
      if (
        typeof src !== 'string' ||
        (!/^https?:\/\//i.test(src) && !src.startsWith('/media/'))
      )
        return <span>{alt || '图片'}</span>;
      return (
        // oxlint-disable-next-line next/no-img-element -- Note images have user-defined dimensions and are already normalized on upload.
        <img
          alt={alt || '笔记图片'}
          decoding="async"
          loading="lazy"
          src={src}
        />
      );
    },
  };

  return (
    <div className="note-markdown">
      <Markdown
        components={components}
        remarkPlugins={[remarkGfm, remarkHighlights]}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
