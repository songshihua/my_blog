'use client';

import { useEffect, useState } from 'react';

import { SiteIcon } from '@/components/ui/site-icon';

const sampleCode = `while not finish():
    draft_tokens = draft.generate(k)
    verified = target.verify(draft_tokens)
    accepted = longest_prefix(verified)
    if accepted < len(draft_tokens):
        resample_from_target()`;

export function ReadingProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    function update() {
      const available =
        document.documentElement.scrollHeight - window.innerHeight;
      setProgress(
        available <= 0
          ? 100
          : Math.min(100, Math.round((window.scrollY / available) * 100)),
      );
    }
    window.addEventListener('scroll', update, { passive: true });
    return () => window.removeEventListener('scroll', update);
  }, []);

  return (
    <div className="progress-card">
      <div className="flex items-center justify-between">
        <span>阅读进度</span>
        <strong>{progress}%</strong>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200">
        <span
          className="block h-full rounded-full bg-brand transition-[width]"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export function CodeBlock() {
  const [copied, setCopied] = useState(false);

  async function copyCode() {
    await navigator.clipboard.writeText(sampleCode);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="article-code">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-[11px] font-semibold text-slate-300">
        <span>伪代码：投机解码主循环</span>
        <button
          className="rounded bg-white/10 px-2 py-1 hover:bg-white/20"
          onClick={copyCode}
          type="button"
        >
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      <pre>
        <code>{sampleCode}</code>
      </pre>
    </div>
  );
}

export function ArticleActions() {
  const [saved, setSaved] = useState(false);

  async function share() {
    if (navigator.share)
      await navigator.share({
        title: document.title,
        url: window.location.href,
      });
    else await navigator.clipboard.writeText(window.location.href);
  }

  return (
    <div className="grid grid-cols-2 divide-x divide-line rounded-lg border border-line bg-white">
      <button
        className="inline-flex items-center justify-center gap-2 py-3 text-sm font-semibold hover:text-brand"
        onClick={() => setSaved((value) => !value)}
        type="button"
      >
        <SiteIcon name="bookmark" />
        {saved ? '已收藏' : '收藏'}
      </button>
      <button
        className="inline-flex items-center justify-center gap-2 py-3 text-sm font-semibold hover:text-brand"
        onClick={share}
        type="button"
      >
        <SiteIcon name="share" />
        分享
      </button>
    </div>
  );
}
