import type { Metadata } from 'next';
import { ChevronRight, Download, FileText, Home } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { ArticleOutline } from '@/components/notes/article-outline';
import {
  ArticleActions,
  ReadingProgress,
} from '@/components/notes/article-tools';
import { NoteDocument } from '@/components/notes/note-document';
import { NoteTreeNav } from '@/components/notes/note-tree';
import { getArticle, getBackendFileUrl, getNoteTree } from '@/lib/api';

type PageProps = { params: Promise<{ slug: string }> };

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticle(slug);
  if (!article) return { title: '笔记不存在' };
  return {
    title: article.title,
    description: article.summary,
    openGraph: {
      title: article.title,
      description: article.summary,
      images: [],
    },
    twitter: {
      card: 'summary',
      title: article.title,
      description: article.summary,
      images: [],
    },
  };
}

export default async function NoteDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const [article, tree] = await Promise.all([getArticle(slug), getNoteTree()]);
  if (!article) notFound();

  const sourceUrl = article.source_file
    ? getBackendFileUrl(article.source_file.download_url)
    : null;
  const articleIndex = tree.articles.findIndex(
    (item) => item.slug === article.slug,
  );
  const previous = articleIndex > 0 ? tree.articles[articleIndex - 1] : null;
  const next =
    articleIndex >= 0 && articleIndex < tree.articles.length - 1
      ? tree.articles[articleIndex + 1]
      : null;

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="notes-workspace">
        <aside className="notes-library-pane">
          <NoteTreeNav activeSlug={article.slug} tree={tree} />
        </aside>

        <article className="note-reader">
          <nav aria-label="面包屑" className="note-breadcrumb">
            <Link aria-label="笔记首页" href="/notes">
              <Home aria-hidden="true" />
            </Link>
            {article.category.ancestors.map((ancestor) => (
              <span key={ancestor.slug}>
                <ChevronRight aria-hidden="true" />
                {ancestor.name}
              </span>
            ))}
            <span>
              <ChevronRight aria-hidden="true" />
              {article.category.name}
            </span>
          </nav>

          <header className="note-reader-header">
            <div className="flex flex-wrap items-center gap-2">
              {article.source_file ? (
                <span className="note-format-badge">
                  {article.source_file.source_format_label}
                </span>
              ) : (
                article.is_demo && (
                  <span className="demo-badge">示例文章 / SAMPLE</span>
                )
              )}
              <span className="text-xs font-semibold text-brand">
                {article.category.name}
              </span>
            </div>
            <h1>{article.title}</h1>
            {article.summary && <p>{article.summary}</p>}
            <div className="note-reader-meta">
              <span>更新于 {formatDate(article.updated_at)}</span>
              <span>约 {article.reading_minutes} 分钟阅读</span>
              {article.source_file && (
                <span>
                  {Math.max(
                    1,
                    Math.ceil(article.source_file.size_bytes / 1024),
                  )}{' '}
                  KB 原文件
                </span>
              )}
            </div>
            {article.topics.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {article.topics.map((topic) => (
                  <span className="tag-chip" key={topic.slug}>
                    {topic.name}
                  </span>
                ))}
              </div>
            )}
          </header>

          <NoteDocument
            markdown={
              article.body_markdown ||
              article.summary ||
              '该文件暂未提取出可展示的正文。'
            }
            outline={article.outline ?? []}
            title={article.title}
          />

          {(previous || next) && (
            <nav aria-label="相邻笔记" className="note-reader-pager">
              {previous ? (
                <Link href={`/notes/${previous.slug}`}>
                  <span>上一篇</span>
                  {previous.title}
                </Link>
              ) : (
                <span />
              )}
              {next ? (
                <Link className="text-right" href={`/notes/${next.slug}`}>
                  <span>下一篇</span>
                  {next.title}
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </article>

        <aside className="notes-outline-pane">
          <div className="notes-info-sticky space-y-4">
            <ArticleOutline
              items={article.outline ?? []}
              title={article.title}
            />
            <ReadingProgress />
            {article.source_file && sourceUrl && (
              <section className="side-card">
                <h2>原始文件</h2>
                <div className="note-source-file">
                  <FileText aria-hidden="true" />
                  <div>
                    <strong>{article.source_file.original_filename}</strong>
                    <span>{article.source_file.source_format_label}</span>
                  </div>
                </div>
                <a className="secondary-action mt-4 w-full" href={sourceUrl}>
                  <Download aria-hidden="true" /> 下载原文件
                </a>
              </section>
            )}
            <ArticleActions />
          </div>
        </aside>
      </div>
      <SiteFooter />
    </main>
  );
}
