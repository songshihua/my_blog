'use client';

import {
  ArrowLeft,
  Bold,
  Code2,
  Eye,
  Heading2,
  ImagePlus,
  Italic,
  Link2,
  List,
  ListOrdered,
  Pencil,
  Quote,
  Save,
  UploadCloud,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import {
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type ReactNode,
  type SyntheticEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  getNoteCategoryPath,
  orderNoteCategories,
} from '@/components/notes/note-category-utils';
import { NoteDocument } from '@/components/notes/note-document';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import {
  createNoteArticle,
  NoteAuthoringRequestError,
  updateNoteArticle,
  uploadNoteImage,
} from '@/lib/api';
import type {
  Article,
  ArticleOutlineItem,
  NoteCategory,
} from '@/lib/site-data';

type EditorMode = 'write' | 'preview';
type HighlightColor = 'yellow' | 'green' | 'blue' | 'purple' | 'pink';

const HIGHLIGHT_COLORS: Array<{
  value: HighlightColor;
  label: string;
  className: string;
}> = [
  { value: 'yellow', label: '黄色高亮', className: 'bg-amber-300' },
  { value: 'green', label: '绿色高亮', className: 'bg-emerald-300' },
  { value: 'blue', label: '蓝色高亮', className: 'bg-sky-300' },
  { value: 'purple', label: '紫色高亮', className: 'bg-violet-300' },
  { value: 'pink', label: '粉色高亮', className: 'bg-pink-300' },
];

function deriveOutline(markdown: string): ArticleOutlineItem[] {
  const items: ArticleOutlineItem[] = [];
  const used = new Map<string, number>();
  let inFence = false;
  for (const line of markdown.split('\n')) {
    const value = line.trim();
    if (value.startsWith('```') || value.startsWith('~~~')) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const match = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(value);
    if (!match) continue;
    const text = match[2]
      .replace(/==(?:(?:yellow|green|blue|purple|pink)\|)?(.+?)==/g, '$1')
      .replace(/[`*_~]/g, '')
      .trim();
    if (!text) continue;
    const base =
      text
        .normalize('NFKC')
        .toLocaleLowerCase()
        .replace(/[^\p{L}\p{N}_]+/gu, '-')
        .replace(/^[-_]+|[-_]+$/g, '')
        .slice(0, 120) || `section-${items.length + 1}`;
    const count = (used.get(base) ?? 0) + 1;
    used.set(base, count);
    items.push({
      id: count === 1 ? base : `${base}-${count}`,
      text: text.slice(0, 200),
      level: match[1].length,
    });
  }
  return items;
}

function ToolbarButton({
  label,
  children,
  onClick,
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="note-editor-tool"
      onClick={onClick}
      title={label}
      type="button"
    >
      {children}
    </button>
  );
}

export function NoteEditor({
  categories,
  initialArticle,
  authoringEnabled,
}: {
  categories: NoteCategory[];
  initialArticle?: Article;
  authoringEnabled: boolean;
}) {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const orderedCategories = useMemo(
    () => orderNoteCategories(categories),
    [categories],
  );
  const [title, setTitle] = useState(initialArticle?.title ?? '');
  const [summary, setSummary] = useState(initialArticle?.summary ?? '');
  const [categorySlug, setCategorySlug] = useState(
    initialArticle?.category.slug ?? orderedCategories[0]?.slug ?? '',
  );
  const [body, setBody] = useState(initialArticle?.body_markdown ?? '');
  const [mode, setMode] = useState<EditorMode>('write');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const outline = useMemo(() => deriveOutline(body), [body]);

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (!dirty) return;
      event.preventDefault();
    }
    function handleSaveShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        formRef.current?.requestSubmit();
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('keydown', handleSaveShortcut);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('keydown', handleSaveShortcut);
    };
  }, [dirty]);

  function updateBody(value: string) {
    setBody(value);
    setDirty(true);
    setError('');
  }

  function replaceSelection(
    prefix: string,
    suffix: string,
    placeholder: string,
  ) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = body.slice(start, end) || placeholder;
    updateBody(
      `${body.slice(0, start)}${prefix}${selected}${suffix}${body.slice(end)}`,
    );
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + prefix.length,
        start + prefix.length + selected.length,
      );
    });
  }

  function prefixSelectedLines(prefix: string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const lineStart = body.lastIndexOf('\n', Math.max(0, start - 1)) + 1;
    const selected = body.slice(lineStart, end) || '列表项';
    const replacement = selected
      .split('\n')
      .map((line, index) =>
        prefix === '1. ' ? `${index + 1}. ${line}` : `${prefix}${line}`,
      )
      .join('\n');
    updateBody(
      `${body.slice(0, lineStart)}${replacement}${body.slice(end)}`,
    );
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(lineStart, lineStart + replacement.length);
    });
  }

  function applyHighlight(color: HighlightColor) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = body.slice(start, end);
    const wrapped = /^==(yellow|green|blue|purple|pink)\|([\s\S]+)==$/.exec(
      selected,
    );
    if (wrapped) {
      const replacement = `==${color}|${wrapped[2]}==`;
      updateBody(`${body.slice(0, start)}${replacement}${body.slice(end)}`);
      requestAnimationFrame(() => {
        textarea.focus();
        const contentStart = start + color.length + 3;
        textarea.setSelectionRange(contentStart, contentStart + wrapped[2].length);
      });
      return;
    }

    const opening = body
      .slice(0, start)
      .match(/==(yellow|green|blue|purple|pink)\|$/);
    if (opening && body.slice(end).startsWith('==')) {
      const openingStart = start - opening[0].length;
      const replacement = `==${color}|`;
      updateBody(
        `${body.slice(0, openingStart)}${replacement}${body.slice(start)}`,
      );
      requestAnimationFrame(() => {
        textarea.focus();
        const contentStart = openingStart + replacement.length;
        textarea.setSelectionRange(contentStart, contentStart + selected.length);
      });
      return;
    }
    replaceSelection(`==${color}|`, '==', '高亮内容');
  }

  function insertBlock(text: string, start?: number, end?: number) {
    const textarea = textareaRef.current;
    const selectionStart = start ?? textarea?.selectionStart ?? body.length;
    const selectionEnd = end ?? textarea?.selectionEnd ?? selectionStart;
    const prefix = selectionStart > 0 && body[selectionStart - 1] !== '\n' ? '\n\n' : '';
    const suffix =
      selectionEnd < body.length && body[selectionEnd] !== '\n' ? '\n\n' : '\n';
    const insertion = `${prefix}${text}${suffix}`;
    updateBody(
      `${body.slice(0, selectionStart)}${insertion}${body.slice(selectionEnd)}`,
    );
    requestAnimationFrame(() => {
      textarea?.focus();
      const cursor = selectionStart + insertion.length;
      textarea?.setSelectionRange(cursor, cursor);
    });
  }

  async function addImage(file: File) {
    if (uploading) return;
    const accepted = new Set(['image/jpeg', 'image/png', 'image/webp']);
    if (!accepted.has(file.type)) {
      setError('仅支持 JPEG、PNG 和 WebP 图片。');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('图片不能超过 5 MB。');
      return;
    }
    const textarea = textareaRef.current;
    const start = textarea?.selectionStart ?? body.length;
    const end = textarea?.selectionEnd ?? start;
    const safeAlt = file.name
      .replace(/\.[^.]+$/, '')
      .replace(/[[\]\\]/g, '')
      .trim();
    const pendingMarker = `![正在上传 ${safeAlt || '图片'}](note-upload://${crypto.randomUUID()})`;
    insertBlock(pendingMarker, start, end);
    setUploading(true);
    setError('');
    try {
      const image = await uploadNoteImage(file);
      setBody((current) =>
        current.replace(
          pendingMarker,
          `![${safeAlt || '笔记图片'}](${image.url})`,
        ),
      );
      setDirty(true);
    } catch (cause) {
      setBody((current) => current.replace(pendingMarker, ''));
      setError(
        cause instanceof NoteAuthoringRequestError
          ? cause.message
          : '图片上传失败，请稍后重试。',
      );
    } finally {
      setUploading(false);
      if (imageInputRef.current) imageInputRef.current.value = '';
    }
  }

  function chooseImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void addImage(file);
  }

  function pasteImage(event: ClipboardEvent<HTMLTextAreaElement>) {
    const file = [...event.clipboardData.items]
      .find((item) => item.kind === 'file' && item.type.startsWith('image/'))
      ?.getAsFile();
    if (!file) return;
    event.preventDefault();
    void addImage(file);
  }

  function dropImage(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = [...event.dataTransfer.files].find((item) =>
      item.type.startsWith('image/'),
    );
    if (file) void addImage(file);
  }

  async function submit(
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ) {
    event.preventDefault();
    if (saving || uploading) return;
    if (!title.trim()) {
      setError('请输入笔记标题。');
      return;
    }
    if (!categorySlug) {
      setError('请选择笔记分类。');
      return;
    }
    if (!body.trim()) {
      setError('请先写一些笔记内容。');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const input = {
        title,
        summary,
        categorySlug,
        bodyMarkdown: body,
      };
      const article = initialArticle
        ? await updateNoteArticle(initialArticle.slug, input)
        : await createNoteArticle(input);
      setDirty(false);
      router.push(`/notes/${article.slug}`);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof NoteAuthoringRequestError
          ? cause.message
          : '保存失败，请稍后重试。',
      );
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    if (dirty && !window.confirm('有尚未保存的内容，确定离开编辑页吗？')) {
      return;
    }
    router.push(initialArticle ? `/notes/${initialArticle.slug}` : '/notes');
  }

  if (!authoringEnabled) {
    return (
      <section className="note-editor-unavailable">
        <Pencil aria-hidden="true" />
        <h1>写作功能当前未启用</h1>
        <p>请在本地受信任环境中启动 Django 写作服务后再试。</p>
        <Button onClick={() => router.push('/notes')} variant="outline">
          <ArrowLeft /> 返回笔记库
        </Button>
      </section>
    );
  }

  return (
    <form className="note-editor-layout" onSubmit={submit} ref={formRef}>
      <section className="note-editor-main">
        <header className="note-editor-header">
          <button
            aria-label="返回笔记库"
            className="note-editor-back"
            onClick={cancel}
            type="button"
          >
            <ArrowLeft />
          </button>
          <div className="min-w-0 flex-1">
            <span>{initialArticle ? 'EDIT NOTE' : 'NEW NOTE'}</span>
            <Input
              aria-label="笔记标题"
              className="note-editor-title"
              maxLength={200}
              onChange={(event) => {
                setTitle(event.target.value);
                setDirty(true);
              }}
              placeholder="给这篇笔记起个标题"
              required
              value={title}
            />
          </div>
          <Button
            className="hidden sm:inline-flex"
            disabled={saving || uploading}
            type="submit"
          >
            <Save /> {saving ? '保存中' : '保存笔记'}
          </Button>
          <Button
            aria-label={saving ? '正在保存' : '保存笔记'}
            className="sm:hidden"
            disabled={saving || uploading}
            size="icon"
            title="保存笔记"
            type="submit"
          >
            <Save />
          </Button>
        </header>

        <div className="note-editor-mobile-tabs" role="tablist">
          <button
            aria-selected={mode === 'write'}
            className={mode === 'write' ? 'active' : ''}
            onClick={() => setMode('write')}
            role="tab"
            type="button"
          >
            <Pencil /> 编辑
          </button>
          <button
            aria-selected={mode === 'preview'}
            className={mode === 'preview' ? 'active' : ''}
            onClick={() => setMode('preview')}
            role="tab"
            type="button"
          >
            <Eye /> 预览
          </button>
        </div>

        <div className="note-editor-toolbar" aria-label="笔记格式工具栏">
          <div className="note-editor-tool-group">
            <ToolbarButton
              label="二级标题"
              onClick={() => prefixSelectedLines('## ')}
            >
              <Heading2 />
            </ToolbarButton>
            <ToolbarButton
              label="粗体"
              onClick={() => replaceSelection('**', '**', '重点内容')}
            >
              <Bold />
            </ToolbarButton>
            <ToolbarButton
              label="斜体"
              onClick={() => replaceSelection('*', '*', '强调内容')}
            >
              <Italic />
            </ToolbarButton>
            <ToolbarButton
              label="行内代码"
              onClick={() => replaceSelection('`', '`', 'code')}
            >
              <Code2 />
            </ToolbarButton>
          </div>
          <div className="note-editor-tool-group">
            <ToolbarButton label="无序列表" onClick={() => prefixSelectedLines('- ')}>
              <List />
            </ToolbarButton>
            <ToolbarButton label="有序列表" onClick={() => prefixSelectedLines('1. ')}>
              <ListOrdered />
            </ToolbarButton>
            <ToolbarButton label="引用" onClick={() => prefixSelectedLines('> ')}>
              <Quote />
            </ToolbarButton>
            <ToolbarButton
              label="链接"
              onClick={() => replaceSelection('[', '](https://)', '链接文字')}
            >
              <Link2 />
            </ToolbarButton>
          </div>
          <div className="note-editor-tool-group note-editor-highlight-tools">
            <span>高亮</span>
            {HIGHLIGHT_COLORS.map((color) => (
              <button
                aria-label={color.label}
                className={`note-highlight-swatch ${color.className}`}
                key={color.value}
                onClick={() => applyHighlight(color.value)}
                title={color.label}
                type="button"
              />
            ))}
          </div>
          <div className="note-editor-tool-group">
            <ToolbarButton
              label="插入图片"
              onClick={() => imageInputRef.current?.click()}
            >
              {uploading ? <UploadCloud className="animate-pulse" /> : <ImagePlus />}
            </ToolbarButton>
            <input
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={chooseImage}
              ref={imageInputRef}
              type="file"
            />
          </div>
        </div>

        {error && (
          <p className="note-editor-inline-error" role="alert">
            {error}
          </p>
        )}

        <div
          className={`note-editor-panes ${dragging ? 'is-dragging' : ''}`}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={dropImage}
        >
          <section
            aria-label="Markdown 编辑区"
            className={`note-editor-write-pane ${mode === 'preview' ? 'mobile-hidden' : ''}`}
          >
            <textarea
              aria-label="笔记正文"
              onChange={(event) => updateBody(event.target.value)}
              onPaste={pasteImage}
              placeholder={'从这里开始记录…\n\n支持 Markdown，也可以直接粘贴或拖入图片。'}
              ref={textareaRef}
              spellCheck="true"
              value={body}
            />
          </section>
          <section
            aria-label="笔记实时预览"
            className={`note-editor-preview-pane ${mode === 'write' ? 'mobile-hidden' : ''}`}
          >
            {body.trim() ? (
              <NoteDocument markdown={body} outline={outline} title={title} />
            ) : (
              <div className="note-editor-empty-preview">
                <Eye aria-hidden="true" />
                <p>写下内容后，这里会显示排版效果。</p>
              </div>
            )}
          </section>
          {dragging && (
            <div className="note-editor-drop-hint">
              <UploadCloud /> 松开即可插入图片
            </div>
          )}
        </div>

        <footer className="note-editor-statusbar">
          <span>{body.length.toLocaleString('zh-CN')} 字符</span>
          <span>{outline.length} 个标题</span>
          <span>{uploading ? '正在处理图片…' : dirty ? '尚未保存' : '已同步'}</span>
        </footer>
      </section>

      <aside className="note-editor-settings">
        <div className="note-editor-settings-sticky">
          <section className="side-card">
            <span className="note-editor-settings-label">笔记设置</span>
            <label htmlFor="note-category">所属目录</label>
            <NativeSelect
              className="w-full"
              id="note-category"
              onChange={(event) => {
                setCategorySlug(event.target.value);
                setDirty(true);
              }}
              required
              value={categorySlug}
            >
              <NativeSelectOption value="">选择目录</NativeSelectOption>
              {orderedCategories.map((category) => (
                <NativeSelectOption key={category.slug} value={category.slug}>
                  {getNoteCategoryPath(category)}
                </NativeSelectOption>
              ))}
            </NativeSelect>

            <label htmlFor="note-summary">摘要</label>
            <Textarea
              id="note-summary"
              maxLength={1000}
              onChange={(event) => {
                setSummary(event.target.value);
                setDirty(true);
              }}
              placeholder="可选；留空时会从正文自动生成。"
              rows={5}
              value={summary}
            />
            <span className="note-editor-field-help">
              {summary.length}/1000 字
            </span>
          </section>

          {initialArticle?.source_file && (
            <section className="note-editor-source-notice">
              <strong>原文件会保留</strong>
              <p>
                这里修改的是网页正文，不会改写已导入的{' '}
                {initialArticle.source_file.source_format_label} 原文件。
              </p>
            </section>
          )}

          <section className="note-editor-tip-card">
            <strong>图片与高亮</strong>
            <p>可点击图片按钮，也可粘贴或拖入图片；先选中文字，再点颜色即可高亮。</p>
          </section>

          <div className="note-editor-actions">
            <Button disabled={saving || uploading} type="submit">
              <Save /> {saving ? '保存中' : initialArticle ? '保存修改' : '发布笔记'}
            </Button>
            <Button disabled={saving} onClick={cancel} type="button" variant="outline">
              取消
            </Button>
            <span>快捷键 Ctrl / ⌘ + S</span>
          </div>
        </div>
      </aside>
    </form>
  );
}
