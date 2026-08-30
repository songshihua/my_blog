'use client';

import { useMemo, useState } from 'react';
import {
  BookOpen,
  FileText,
  Folder,
  Settings2,
  Trash2,
  TriangleAlert,
} from 'lucide-react';
import { useRouter } from 'next/navigation';

import {
  getNoteCategoryPath,
  orderNoteCategories,
} from '@/components/notes/note-category-utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  deleteNoteArticle,
  deleteNoteCategory,
  NoteManagementRequestError,
} from '@/lib/api';
import type { Article, NoteCategory } from '@/lib/site-data';

type PendingDeletion = {
  kind: 'article' | 'category';
  slug: string;
  name: string;
  path: string;
};

export function NoteManagerDialog({
  categories,
  articles,
  activeSlug,
}: {
  categories: NoteCategory[];
  articles: Article[];
  activeSlug?: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [managedCategories, setManagedCategories] = useState(categories);
  const [managedArticles, setManagedArticles] = useState(articles);
  const [pending, setPending] = useState<PendingDeletion | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const orderedCategories = useMemo(
    () => orderNoteCategories(managedCategories),
    [managedCategories],
  );
  const categoryBySlug = useMemo(
    () =>
      new Map(managedCategories.map((category) => [category.slug, category])),
    [managedCategories],
  );
  const categoryArticleCounts = useMemo(() => {
    const counts = new Map<string, number>();
    managedArticles.forEach((article) =>
      counts.set(
        article.category.slug,
        (counts.get(article.category.slug) ?? 0) + 1,
      ),
    );
    return counts;
  }, [managedArticles]);
  const categoriesWithChildren = useMemo(
    () =>
      new Set(
        managedCategories
          .map((category) => category.parent_slug)
          .filter((slug): slug is string => Boolean(slug)),
      ),
    [managedCategories],
  );
  const orderedArticles = useMemo(
    () =>
      [...managedArticles].sort((left, right) => {
        const categoryOrder = getNoteCategoryPath(left.category).localeCompare(
          getNoteCategoryPath(right.category),
          'zh-CN',
        );
        return categoryOrder || left.title.localeCompare(right.title, 'zh-CN');
      }),
    [managedArticles],
  );

  function changeOpen(nextOpen: boolean) {
    if (submitting) return;
    setOpen(nextOpen);
    if (nextOpen) {
      setManagedCategories(categories);
      setManagedArticles(articles);
      setPending(null);
      setError('');
      setSuccess('');
    }
  }

  async function confirmDelete() {
    if (!pending) return;
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      if (pending.kind === 'article') {
        await deleteNoteArticle(pending.slug);
        setManagedArticles((current) =>
          current.filter((article) => article.slug !== pending.slug),
        );
        setSuccess(`文章“${pending.name}”已删除。`);
      } else {
        await deleteNoteCategory(pending.slug);
        setManagedCategories((current) =>
          current.filter((category) => category.slug !== pending.slug),
        );
        setSuccess(`目录“${pending.name}”已删除。`);
      }

      const deletedActiveArticle =
        pending.kind === 'article' && pending.slug === activeSlug;
      setPending(null);
      if (deletedActiveArticle) {
        setOpen(false);
        router.push('/notes');
      }
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof NoteManagementRequestError
          ? cause.message
          : '删除失败，请稍后重试。',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger
        render={
          <Button className="h-10 w-full justify-center" variant="outline" />
        }
      >
        <Settings2 /> 管理笔记
      </DialogTrigger>
      <DialogContent className="note-author-dialog max-h-[calc(100vh-2rem)] overflow-hidden sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-black">
            <BookOpen className="size-5 text-brand" /> 笔记与目录管理
          </DialogTitle>
          <DialogDescription>
            删除文章后不可恢复；目录必须为空，且不包含子目录时才能删除。
          </DialogDescription>
        </DialogHeader>

        {pending && (
          <section
            className="rounded-xl border border-red-200 bg-red-50 p-4"
            aria-live="assertive"
          >
            <div className="flex gap-3">
              <TriangleAlert className="mt-0.5 size-5 shrink-0 text-red-600" />
              <div className="min-w-0 flex-1">
                <h3 className="font-bold text-red-800">
                  确认删除{pending.kind === 'article' ? '文章' : '目录'}？
                </h3>
                <p className="mt-1 break-words text-xs leading-5 text-red-700">
                  {pending.path}
                </p>
                <p className="mt-2 text-xs font-semibold text-red-800">
                  此操作不可撤销。
                </p>
              </div>
            </div>
            <div className="mt-3 flex justify-end gap-2">
              <Button
                disabled={submitting}
                onClick={() => setPending(null)}
                variant="outline"
              >
                取消
              </Button>
              <Button
                disabled={submitting}
                onClick={confirmDelete}
                variant="destructive"
              >
                <Trash2 /> {submitting ? '正在删除' : '确认删除'}
              </Button>
            </div>
          </section>
        )}

        {error && (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            role="alert"
          >
            {error}
          </p>
        )}
        {success && (
          <output className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {success}
          </output>
        )}

        <div className="min-h-0 space-y-5 overflow-y-auto pr-1">
          <section>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="flex items-center gap-2 font-bold">
                <Folder className="size-4 text-brand" /> 目录
              </h3>
              <span className="text-xs text-muted-ink">
                {managedCategories.length} 个
              </span>
            </div>
            <div className="space-y-2">
              {orderedCategories.length ? (
                orderedCategories.map((category) => {
                  const articleCount =
                    categoryArticleCounts.get(category.slug) ?? 0;
                  const hasChildren = categoriesWithChildren.has(category.slug);
                  const canDelete = articleCount === 0 && !hasChildren;
                  const reason = hasChildren
                    ? '请先删除子目录'
                    : articleCount > 0
                      ? `请先删除目录内 ${articleCount} 篇文章`
                      : '删除空目录';
                  return (
                    <div
                      className="flex items-center gap-3 rounded-lg border border-line bg-white px-3 py-2"
                      key={category.slug}
                    >
                      <Folder className="size-4 shrink-0 text-amber-500" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold">
                          {getNoteCategoryPath(category)}
                        </p>
                        <p className="text-[11px] text-muted-ink">{reason}</p>
                      </div>
                      <Button
                        aria-label={`删除目录 ${category.name}`}
                        disabled={!canDelete || submitting}
                        onClick={() =>
                          setPending({
                            kind: 'category',
                            slug: category.slug,
                            name: category.name,
                            path: getNoteCategoryPath(category),
                          })
                        }
                        size="sm"
                        title={reason}
                        variant="destructive"
                      >
                        <Trash2 /> 删除
                      </Button>
                    </div>
                  );
                })
              ) : (
                <p className="rounded-lg border border-dashed border-line p-4 text-center text-xs text-muted-ink">
                  暂无目录。
                </p>
              )}
            </div>
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="flex items-center gap-2 font-bold">
                <FileText className="size-4 text-brand" /> 文章
              </h3>
              <span className="text-xs text-muted-ink">
                {managedArticles.length} 篇
              </span>
            </div>
            <div className="space-y-2">
              {orderedArticles.length ? (
                orderedArticles.map((article) => {
                  const category =
                    categoryBySlug.get(article.category.slug) ??
                    article.category;
                  return (
                    <div
                      className="flex items-center gap-3 rounded-lg border border-line bg-white px-3 py-2"
                      key={article.slug}
                    >
                      <FileText className="size-4 shrink-0 text-brand" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold">
                          {article.title}
                        </p>
                        <p className="truncate text-[11px] text-muted-ink">
                          {getNoteCategoryPath(category)}
                        </p>
                      </div>
                      <Button
                        aria-label={`删除文章 ${article.title}`}
                        disabled={submitting}
                        onClick={() =>
                          setPending({
                            kind: 'article',
                            slug: article.slug,
                            name: article.title,
                            path: `${getNoteCategoryPath(category)} / ${article.title}`,
                          })
                        }
                        size="sm"
                        variant="destructive"
                      >
                        <Trash2 /> 删除
                      </Button>
                    </div>
                  );
                })
              ) : (
                <p className="rounded-lg border border-dashed border-line p-4 text-center text-xs text-muted-ink">
                  暂无文章。
                </p>
              )}
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
