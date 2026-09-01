import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { NoteEditor } from '@/components/notes/note-editor';
import { NoteTreeNav } from '@/components/notes/note-tree';
import { getArticle, getNoteTree } from '@/lib/api';

type PageProps = { params: Promise<{ slug: string }> };

export const metadata: Metadata = {
  title: '编辑笔记',
  robots: { index: false, follow: false },
};

export default async function EditNotePage({ params }: PageProps) {
  const { slug } = await params;
  const [article, tree] = await Promise.all([getArticle(slug), getNoteTree()]);
  if (!article) notFound();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="notes-workspace notes-editor-workspace">
        <aside className="notes-library-pane">
          <NoteTreeNav activeSlug={article.slug} tree={tree} />
        </aside>
        <NoteEditor
          authoringEnabled={tree.authoring_enabled ?? tree.import_enabled}
          categories={tree.categories}
          initialArticle={article}
        />
      </div>
      <SiteFooter />
    </main>
  );
}
