import type { Metadata } from 'next';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { NoteEditor } from '@/components/notes/note-editor';
import { NoteTreeNav } from '@/components/notes/note-tree';
import { getNoteTree } from '@/lib/api';

export const metadata: Metadata = {
  title: '新建笔记',
  description: '在笔记知识库中创建并排版一篇新笔记。',
};

export default async function NewNotePage() {
  const tree = await getNoteTree();
  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="notes-workspace notes-editor-workspace">
        <aside className="notes-library-pane">
          <NoteTreeNav tree={tree} />
        </aside>
        <NoteEditor
          authoringEnabled={tree.authoring_enabled ?? tree.import_enabled}
          categories={tree.categories}
        />
      </div>
      <SiteFooter />
    </main>
  );
}
