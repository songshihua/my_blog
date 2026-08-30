'use client';

import { useMemo, useState, type SyntheticEvent } from 'react';
import { FolderPlus } from 'lucide-react';
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
import { NoteCategoryRequestError, createNoteCategory } from '@/lib/api';
import type { NoteCategory } from '@/lib/site-data';

export function NoteCategoryDialog({
  categories,
  maxDepth,
}: {
  categories: NoteCategory[];
  maxDepth: number;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const possibleParents = useMemo(
    () =>
      orderNoteCategories(categories).filter(
        (category) => category.ancestors.length + 1 < maxDepth,
      ),
    [categories, maxDepth],
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
    const nameValue = form.get('name');
    const parentValue = form.get('parent_slug');
    const name = typeof nameValue === 'string' ? nameValue.trim() : '';
    const parentSlug =
      typeof parentValue === 'string' && parentValue ? parentValue : null;
    if (!name) {
      setError('请输入目录名称。');
      return;
    }

    setSubmitting(true);
    try {
      await createNoteCategory({ name, parentSlug });
      setOpen(false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof NoteCategoryRequestError
          ? cause.message
          : '新建目录失败，请稍后重试。',
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
        <FolderPlus /> 新建目录
      </DialogTrigger>
      <DialogContent className="note-author-dialog sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-black">新建笔记目录</DialogTitle>
          <DialogDescription>
            选择上级目录后即可逐级建立子目录，最多支持 {maxDepth} 层。
          </DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={submit}>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-category-name"
          >
            目录名称
            <Input
              autoComplete="off"
              id="note-category-name"
              maxLength={80}
              name="name"
              placeholder="例如：模型部署"
              required
            />
          </label>
          <label
            className="grid gap-1.5 text-sm font-semibold"
            htmlFor="note-parent-category"
          >
            上级目录
            <NativeSelect
              className="w-full bg-white"
              defaultValue=""
              id="note-parent-category"
              name="parent_slug"
            >
              <NativeSelectOption value="">
                根目录（新建一级目录）
              </NativeSelectOption>
              {possibleParents.map((category) => (
                <NativeSelectOption key={category.slug} value={category.slug}>
                  {getNoteCategoryPath(category)}
                </NativeSelectOption>
              ))}
            </NativeSelect>
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
              ? '正在创建目录……'
              : '目录会保存在数据库中，刷新或重启后仍会保留。'}
          </p>
          <DialogFooter className="note-author-dialog-footer mt-1">
            <Button disabled={submitting} size="lg" type="submit">
              <FolderPlus /> {submitting ? '正在创建' : '创建目录'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
