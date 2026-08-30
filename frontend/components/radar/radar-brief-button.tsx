'use client';

import { useState } from 'react';

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

export function RadarBriefButton() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [brief, setBrief] = useState<RadarBrief | null>(null);

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
        <DialogContent className="max-h-[calc(100vh-2rem)] overflow-y-auto sm:max-w-2xl">
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
            </article>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
