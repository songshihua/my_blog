import type { Metadata } from 'next';
import { FileText, FolderTree, PencilLine, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { NoteTreeNav } from '@/components/notes/note-tree';
import { getNoteTree } from '@/lib/api';

export const metadata: Metadata = {
  title: '技术笔记',
  description: '按主题分层整理的研究与开发笔记知识库。',
};

function formatDate(value: string | null) {
  if (!value) return '尚未发布';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value));
}

export default async function NotesPage() {
  const tree = await getNoteTree();
  const recentArticles = [...tree.articles]
    .sort((left, right) =>
      (right.published_at ?? '').localeCompare(left.published_at ?? ''),
    )
    .slice(0, 12);
  const formats = new Set(
    tree.articles
      .map((article) => article.source_file?.source_format_label)
      .filter((value): value is string => Boolean(value)),
  );

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="notes-workspace notes-workspace-index">
        <aside className="notes-library-pane">
          <NoteTreeNav tree={tree} />
        </aside>

        <section className="notes-index-pane">
          <header className="notes-index-header">
            <div>
              <span>RESEARCH NOTES</span>
              <h1>技术笔记知识库</h1>
              <p>
                像目录一样逐层归档内容，可直接写作、插入图片与彩色高亮，也可以导入已有文件。
              </p>
              {(tree.authoring_enabled ?? tree.import_enabled) && (
                <Link className="primary-action mt-5" href="/notes/new">
                  <PencilLine aria-hidden="true" /> 开始写笔记
                </Link>
              )}
            </div>
            <div
              className="notes-index-count"
              aria-label={`共 ${tree.articles.length} 篇笔记`}
            >
              <strong>{tree.articles.length}</strong>
              <span>篇笔记</span>
            </div>
          </header>

          <div className="notes-section-heading">
            <div>
              <h2>最近更新</h2>
              <p>导入完成后，笔记会立即出现在所属分类和这里。</p>
            </div>
          </div>

          {recentArticles.length ? (
            <div className="notes-index-list">
              {recentArticles.map((article) => {
                const categoryPath = [
                  ...article.category.ancestors,
                  article.category,
                ]
                  .map((category) => category.name)
                  .join(' / ');
                return (
                  <Link
                    className="note-index-card group"
                    href={`/notes/${article.slug}`}
                    key={article.slug}
                  >
                    <div className="note-index-icon">
                      <FileText aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="note-index-path">{categoryPath}</span>
                        {article.source_file ? (
                          <span className="note-format-badge">
                            {article.source_file.source_format_label}
                          </span>
                        ) : (
                          article.is_demo && (
                            <span className="demo-badge">示例</span>
                          )
                        )}
                      </div>
                      <h3>{article.title}</h3>
                      <p>{article.summary}</p>
                      <div className="note-index-meta">
                        <time dateTime={article.published_at ?? undefined}>
                          {formatDate(article.published_at)}
                        </time>
                        <span>{article.reading_minutes} 分钟阅读</span>
                      </div>
                    </div>
                    <span className="note-index-arrow" aria-hidden="true">
                      →
                    </span>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <FileText
                className="mx-auto mb-3 size-8 text-brand"
                aria-hidden="true"
              />
              还没有笔记。请先在左侧选择“添加笔记”。
            </div>
          )}
        </section>

        <aside className="notes-info-pane">
          <div className="notes-info-sticky">
            <section className="side-card">
              <FolderTree aria-hidden="true" className="notes-info-icon" />
              <h2>分层管理</h2>
              <p>
                当前共有 {tree.categories.length}{' '}
                个分类节点。文章沿父子分类逐层展开，适合持续积累专题知识。
              </p>
            </section>
            <section className="side-card">
              <ShieldCheck aria-hidden="true" className="notes-info-icon" />
              <h2>本地文件</h2>
              <p>
                原文件保存在项目的 <code>data/notes</code>{' '}
                目录，不会作为公开媒体文件直接暴露。
              </p>
              <dl className="notes-facts">
                <div>
                  <dt>支持格式</dt>
                  <dd>MD / DOCX / PDF</dd>
                </div>
                <div>
                  <dt>已导入格式</dt>
                  <dd>{formats.size ? [...formats].join(' / ') : '暂无'}</dd>
                </div>
                <div>
                  <dt>单文件上限</dt>
                  <dd>8 MB</dd>
                </div>
              </dl>
            </section>
          </div>
        </aside>
      </div>
      <SiteFooter />
    </main>
  );
}
