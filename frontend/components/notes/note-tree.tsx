'use client';

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, FileText, PencilLine } from 'lucide-react';
import Link from 'next/link';

import { NoteCategoryDialog } from '@/components/notes/note-category-dialog';
import { NoteManagerDialog } from '@/components/notes/note-manager-dialog';
import { NoteUploadDialog } from '@/components/notes/note-upload-dialog';
import { Button } from '@/components/ui/button';
import type { Article, NoteCategory, NoteTree } from '@/lib/site-data';

type CategoryNode = NoteCategory & {
  children: CategoryNode[];
  articles: Article[];
};

function buildTree(
  categories: NoteCategory[],
  articles: Article[],
): CategoryNode[] {
  const nodes = new Map<string, CategoryNode>();
  categories.forEach((category) =>
    nodes.set(category.slug, { ...category, children: [], articles: [] }),
  );
  articles.forEach((article) =>
    nodes.get(article.category.slug)?.articles.push(article),
  );
  const roots: CategoryNode[] = [];
  nodes.forEach((node) => {
    const parent = node.parent_slug ? nodes.get(node.parent_slug) : null;
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  const sortNodes = (items: CategoryNode[]): CategoryNode[] =>
    items
      .sort(
        (left, right) =>
          left.sort_order - right.sort_order ||
          left.name.localeCompare(right.name, 'zh-CN'),
      )
      .map((item) => ({
        ...item,
        children: sortNodes(item.children),
        articles: [...item.articles].sort((left, right) =>
          (right.published_at ?? '').localeCompare(left.published_at ?? ''),
        ),
      }));
  return sortNodes(roots);
}

function CategoryBranch({
  node,
  activeSlug,
  expanded,
  toggle,
  depth = 0,
}: {
  node: CategoryNode;
  activeSlug?: string;
  expanded: Set<string>;
  toggle: (slug: string) => void;
  depth?: number;
}) {
  const isOpen = expanded.has(node.slug);
  const panelId = `note-category-${node.slug}`;
  const hasContent = node.children.length > 0 || node.articles.length > 0;
  return (
    <li>
      <button
        aria-controls={panelId}
        aria-expanded={isOpen}
        className="note-tree-category"
        onClick={() => toggle(node.slug)}
        style={{ paddingLeft: `${12 + depth * 14}px` }}
        type="button"
      >
        <span className="min-w-0 flex-1 truncate text-left">{node.name}</span>
        {hasContent && (isOpen ? <ChevronDown /> : <ChevronRight />)}
      </button>
      {isOpen && (
        <div id={panelId}>
          {node.articles.length > 0 && (
            <ul>
              {node.articles.map((article) => (
                <li key={article.slug}>
                  <Link
                    aria-current={
                      activeSlug === article.slug ? 'page' : undefined
                    }
                    className={`note-tree-article ${activeSlug === article.slug ? 'note-tree-article-active' : ''}`}
                    href={`/notes/${article.slug}`}
                    style={{ paddingLeft: `${28 + depth * 14}px` }}
                  >
                    <FileText className="size-3.5 shrink-0" />
                    <span>{article.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {node.children.length > 0 && (
            <ul>
              {node.children.map((child) => (
                <CategoryBranch
                  activeSlug={activeSlug}
                  depth={depth + 1}
                  expanded={expanded}
                  key={child.slug}
                  node={child}
                  toggle={toggle}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  );
}

export function NoteTreeNav({
  tree,
  activeSlug,
}: {
  tree: NoteTree;
  activeSlug?: string;
}) {
  const categoryTree = useMemo(
    () => buildTree(tree.categories, tree.articles),
    [tree],
  );
  const [expanded, setExpanded] = useState(
    () => new Set(tree.categories.map((category) => category.slug)),
  );
  const authoringEnabled = tree.authoring_enabled ?? tree.import_enabled;

  function toggle(slug: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-line p-4">
        <Link
          className="text-lg font-black tracking-tight hover:text-brand"
          href="/notes"
        >
          笔记知识库
        </Link>
        <p className="mt-1 text-[11px] text-muted-ink">
          按研究主题逐层组织与沉淀
        </p>
        {tree.import_enabled && (
          <div className="mt-3 grid grid-cols-2 gap-2">
            {authoringEnabled && (
              <Button
                className="col-span-2 h-10 w-full"
                render={<Link href="/notes/new" />}
              >
                <PencilLine /> 写笔记
              </Button>
            )}
            <NoteCategoryDialog
              categories={tree.categories}
              maxDepth={tree.max_category_depth ?? 8}
            />
            <NoteUploadDialog categories={tree.categories} />
            <div className="col-span-2">
              <NoteManagerDialog
                activeSlug={activeSlug}
                articles={tree.articles}
                categories={tree.categories}
              />
            </div>
          </div>
        )}
      </div>
      <nav
        aria-label="笔记分类目录"
        className="min-h-0 flex-1 overflow-y-auto py-2"
      >
        {categoryTree.length ? (
          <ul>
            {categoryTree.map((node) => (
              <CategoryBranch
                activeSlug={activeSlug}
                expanded={expanded}
                key={node.slug}
                node={node}
                toggle={toggle}
              />
            ))}
          </ul>
        ) : (
          <p className="px-4 py-8 text-center text-xs text-muted-ink">
            还没有笔记分类。
          </p>
        )}
      </nav>
      <div className="border-t border-line p-4 text-[11px] leading-5 text-muted-ink">
        支持在线写作、图片、彩色高亮
        <br />
        也可导入 Markdown、Word、PDF
      </div>
    </div>
  );
}
