'use client';

import { useState } from 'react';
import { CheckCircle2, Download } from 'lucide-react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { SiteIcon } from '@/components/ui/site-icon';
import { Spinner } from '@/components/ui/spinner';
import {
  generateRadarBrief,
  RadarBriefRequestError,
  type RadarBrief,
} from '@/lib/api';

function formatDate(value: string) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(date);
}

type SaveFilePicker = (options: {
  suggestedName: string;
  types: Array<{
    description: string;
    accept: Record<string, string[]>;
  }>;
}) => Promise<{
  createWritable: () => Promise<{
    write: (data: Blob) => Promise<void>;
    close: () => Promise<void>;
  }>;
}>;

function briefToMarkdown(brief: RadarBrief) {
  const lines = [
    `# ${brief.title}`,
    '',
    `> 生成时间：${formatDate(brief.generated_at)}  `,
    `> 内容来源：${brief.source_count} 条真实雷达内容  `,
    `> 使用模型：${brief.model}`,
    '',
    '## 简报概览',
    '',
    brief.overview,
    '',
    '## 重点进展',
    '',
  ];

  brief.highlights.forEach((item, index) => {
    const safeTitle = item.title.replaceAll('[', '\\[').replaceAll(']', '\\]');
    lines.push(
      `### ${index + 1}. [${safeTitle}](${item.url})`,
      '',
      item.insight,
      '',
    );
  });

  if (brief.trends.length) {
    lines.push('## 趋势判断', '', ...brief.trends.map((item) => `- ${item}`), '');
  }
  if (brief.watchlist.length) {
    lines.push('## 后续关注', '', ...brief.watchlist.map((item) => `- ${item}`), '');
  }
  lines.push('---', '', '本简报由 AI 基于站内已验证来源生成，请通过条目标题链接核对原文。', '');
  return lines.join('\n');
}

function downloadWithBrowser(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function RadarBriefButton() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [brief, setBrief] = useState<RadarBrief | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [downloadCompleteOpen, setDownloadCompleteOpen] = useState(false);
  const [downloadCompleteMessage, setDownloadCompleteMessage] = useState('');

  async function generate() {
    if (loading) return;
    setOpen(true);
    setLoading(true);
    setError('');
    try {
      setBrief(await generateRadarBrief());
    } catch (cause) {
      setBrief(null);
      setError(
        cause instanceof RadarBriefRequestError
          ? cause.message
          : '简报生成失败，请稍后重试。',
      );
    } finally {
      setLoading(false);
    }
  }

  async function downloadBrief() {
    if (!brief || saving) return;
    setSaving(true);
    setSaveMessage('');
    const date = new Date(brief.generated_at);
    const datePart = Number.isFinite(date.getTime())
      ? date.toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' })
      : 'today';
    const filename = `AI研究简报-${datePart}.md`;
    const blob = new Blob([briefToMarkdown(brief)], {
      type: 'text/markdown;charset=utf-8',
    });

    try {
      const picker = (
        window as Window & { showSaveFilePicker?: SaveFilePicker }
      ).showSaveFilePicker;
      if (picker) {
        const handle = await picker({
          suggestedName: filename,
          types: [
            {
              description: 'Markdown 文档',
              accept: { 'text/markdown': ['.md'] },
            },
          ],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        setSaveMessage('简报已保存到所选路径。');
        setDownloadCompleteMessage(`文件 ${filename} 已保存到你选择的路径。`);
        setDownloadCompleteOpen(true);
      } else {
        downloadWithBrowser(blob, filename);
        setSaveMessage('浏览器不支持选择路径，已保存到默认下载目录。');
        setDownloadCompleteMessage(`文件 ${filename} 已保存到浏览器默认下载目录。`);
        setDownloadCompleteOpen(true);
      }
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        setSaveMessage('已取消下载。');
      } else {
        setSaveMessage('保存失败，请重试或更换保存路径。');
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <button
        aria-busy={loading}
        className="secondary-action w-full"
        disabled={loading}
        onClick={generate}
        type="button"
      >
        {loading ? <Spinner /> : <SiteIcon name="document" />}
        {loading ? '正在撰写简报…' : '生成今日简报'}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[calc(100vh-2rem)] overflow-y-auto border border-slate-200 bg-white text-slate-950 opacity-100 shadow-2xl sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="pr-8 text-xl font-black">
              {brief?.title ?? (loading ? '正在生成今日简报' : '今日简报')}
            </DialogTitle>
            <DialogDescription>
              {brief
                ? `基于 ${brief.source_count} 条真实雷达内容 · ${formatDate(brief.generated_at)}${brief.cached ? ' · 已复用近期结果' : ''}`
                : 'DeepSeek 正在梳理最近 7 天的真实雷达内容。'}
            </DialogDescription>
          </DialogHeader>

          {loading && (
            <div className="grid min-h-52 place-items-center rounded-xl border border-line bg-muted/30 text-sm text-muted-ink">
              <div className="flex items-center gap-2">
                <Spinner /> 正在提炼重点与趋势，请稍候…
              </div>
            </div>
          )}

          {!loading && error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
              <p>{error}</p>
              <button
                className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-1.5 font-semibold"
                onClick={generate}
                type="button"
              >
                重新生成
              </button>
            </div>
          )}

          {!loading && brief && (
            <article className="space-y-5 text-sm leading-7">
              <section>
                <h3 className="mb-1 font-black text-brand">简报概览</h3>
                <p className="text-muted-ink">{brief.overview}</p>
              </section>

              <section>
                <h3 className="mb-2 font-black">重点进展</h3>
                <div className="space-y-2">
                  {brief.highlights.map((item, index) => (
                    <div className="rounded-xl border border-line p-3" key={item.item_id}>
                      <a
                        className="font-bold hover:text-brand"
                        href={item.url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {index + 1}. {item.title} <span aria-hidden="true">↗</span>
                      </a>
                      <p className="mt-1 text-muted-ink">{item.insight}</p>
                    </div>
                  ))}
                </div>
              </section>

              {brief.trends.length > 0 && (
                <section>
                  <h3 className="mb-1 font-black">趋势判断</h3>
                  <ul className="list-disc space-y-1 pl-5 text-muted-ink">
                    {brief.trends.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </section>
              )}

              {brief.watchlist.length > 0 && (
                <section>
                  <h3 className="mb-1 font-black">后续关注</h3>
                  <ul className="list-disc space-y-1 pl-5 text-muted-ink">
                    {brief.watchlist.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </section>
              )}

              <p className="border-t border-line pt-3 text-[11px] text-muted-ink">
                内容由 {brief.model} 基于站内已验证来源生成，请点击标题核对原文。
              </p>

              <div className="sticky -bottom-4 -mx-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-3 shadow-[0_-8px_20px_rgba(15,23,42,0.06)]">
                <p aria-live="polite" className="min-h-5 flex-1 text-xs text-muted-ink">
                  {saveMessage || '下载时可选择保存目录和文件名。'}
                </p>
                <button
                  aria-busy={saving}
                  className="primary-action shrink-0 disabled:cursor-wait disabled:opacity-70"
                  disabled={saving}
                  onClick={downloadBrief}
                  type="button"
                >
                  {saving ? <Spinner /> : <Download className="size-4" />}
                  {saving ? '正在保存…' : '选择路径并下载'}
                </button>
              </div>
            </article>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={downloadCompleteOpen}
        onOpenChange={setDownloadCompleteOpen}
      >
        <AlertDialogContent className="border border-emerald-200 bg-white text-slate-950 opacity-100 shadow-2xl">
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-emerald-50 text-emerald-600">
              <CheckCircle2 />
            </AlertDialogMedia>
            <AlertDialogTitle className="font-black">下载完成</AlertDialogTitle>
            <AlertDialogDescription>
              {downloadCompleteMessage}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="bg-slate-50">
            <AlertDialogAction
              className="w-full sm:w-auto"
              onClick={() => setDownloadCompleteOpen(false)}
            >
              知道了
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
