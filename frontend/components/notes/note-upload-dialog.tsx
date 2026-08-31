'use client';

import { useMemo, useState, type SyntheticEvent } from 'react';
import { FileUp, Plus } from 'lucide-react';
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { NoteImportRequestError, uploadNoteFile } from '@/lib/api';
import type { NoteCategory } from '@/lib/site-data';

export function NoteUploadDialog({
  categories,
}: {
  categories: NoteCategory[];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const sortedCategories = useMemo(
    () => orderNoteCategories(categories),
    [categories],
  );

  function changeOpen(nextOpen: boolean) {
    if (submitting) return;
    setOpen(nextOpen);
    if (nextOpen) setError('');
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    setError('');
    const form = new FormData(event.currentTarget);
    const file = form.get('file');
    const categoryValue = form.get('category_slug');
    const categorySlug = typeof categoryValue === 'string' ? categoryValue : '';
    const titleValue = form.get('title');
    const summaryValue = form.get('summary');
    if (!(file instanceof File) || file.size === 0) {
      setError('请选择一个 Markdown、Word DOCX 或 PDF 文件。');
      return;
    }
    if (!categorySlug) {
      setError('请选择笔记分类。');
      return;
    }

    setSubmitting(true);
    try {
      const article = await uploadNoteFile({
        file,
        categorySlug,
        title: typeof titleValue === 'string' ? titleValue : '',
        summary: typeof summaryValue === 'string' ? summaryValue : '',
      });
      setOpen(false);
      router.push(`/notes/${article.slug}`);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof NoteImportRequestError
          ? cause.message
          : '导入失败，请稍后重试。',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger render={<Button className="h-10 w-full justify-center" />}>
        <Plus /> 添加笔记
      </DialogTrigger>
      <DialogContent className="note-author-dialog sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-black">导入本地笔记</DialogTitle>
          <DialogDescription>
            支持 UTF-8 Markdown、Word DOCX 和 PDF（含扫描版），单个文件不超过 8
            MB。PDF 可在原版视图与文本视图间切换。
          </DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={submit}>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-source-file"
          >
            笔记文件
            <Input
              accept=".md,.markdown,.docx,.pdf,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="h-11 cursor-pointer py-1.5"
              id="note-source-file"
              name="file"
              required
              type="file"
            />
          </label>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-category"
          >
            保存到目录
            <NativeSelect
              className="w-full bg-white"
              defaultValue=""
              id="note-category"
              name="category_slug"
              required
            >
              <NativeSelectOption disabled value="">
                请选择文件保存目录
              </NativeSelectOption>
              {sortedCategories.map((category) => (
                <NativeSelectOption key={category.slug} value={category.slug}>
                  {getNoteCategoryPath(category)}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-title"
          >
            标题（可选）
            <Input
              id="note-title"
              maxLength={200}
              name="title"
              placeholder="默认读取第一个标题或文件名"
            />
          </label>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-summary"
          >
            摘要（可选）
            <Textarea
              id="note-summary"
              maxLength={1000}
              name="summary"
              placeholder="留空时从正文自动生成"
              rows={3}
            />
          </label>
          {error && (
            <p
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              {error}
            </p>
          )}
          <p aria-live="polite" className="text-xs text-muted-ink">
            {submitting
              ? '正在上传并提取内容，请勿关闭窗口……'
              : '原文件将保存到项目 data/notes 目录；扫描版 PDF 暂不支持 OCR。'}
          </p>
          <DialogFooter className="note-author-dialog-footer mt-1">
            <Button
              disabled={submitting || !sortedCategories.length}
              size="lg"
              type="submit"
            >
              <FileUp /> {submitting ? '正在导入' : '导入并发布'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
