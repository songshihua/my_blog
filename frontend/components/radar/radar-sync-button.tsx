'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { RadarSyncRequestError, syncRadarSources } from '@/lib/api';

type SyncPhase = 'idle' | 'syncing' | 'success' | 'partial' | 'error';

const phaseLabel: Record<SyncPhase, string> = {
  idle: '立即同步 ↻',
  syncing: '同步中…',
  success: '同步完成 ✓',
  partial: '部分完成 ↻',
  error: '同步失败，重试',
};

export function RadarSyncButton() {
  const router = useRouter();
  const [phase, setPhase] = useState<SyncPhase>('idle');
  const [message, setMessage] = useState('点击同步 arXiv、GitHub 与 Hugging Face');
  const [retryAfter, setRetryAfter] = useState<number | null>(null);

  useEffect(() => {
    if (phase !== 'success' && phase !== 'partial') return;
    const timer = window.setTimeout(() => setPhase('idle'), 5000);
    return () => window.clearTimeout(timer);
  }, [phase]);

  async function handleSync() {
    if (phase === 'syncing' || retryAfter) return;
    setPhase('syncing');
    setMessage('正在从三个数据源获取最新内容，请稍候。');

    try {
      const result = await syncRadarSources();
      setMessage(result.message);
      setPhase(result.status === 'success' ? 'success' : result.status === 'partial' ? 'partial' : 'error');
      if (result.status !== 'error') router.refresh();
    } catch (error) {
      const syncError = error instanceof RadarSyncRequestError
        ? error
        : new RadarSyncRequestError('同步失败，请稍后重试。');
      setMessage(syncError.message);
      setPhase('error');
      if (syncError.retryAfter) setRetryAfter(syncError.retryAfter);
    }
  }

  useEffect(() => {
    if (!retryAfter) return;
    const timer = window.setInterval(() => {
      setRetryAfter((current) => current && current > 1 ? current - 1 : null);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [retryAfter]);

  const label = retryAfter ? `${retryAfter} 秒后重试` : phaseLabel[phase];

  return (
    <button
      aria-busy={phase === 'syncing'}
      aria-label={`${label}。${message}`}
      className="primary-action disabled:cursor-wait disabled:opacity-70"
      disabled={phase === 'syncing' || Boolean(retryAfter)}
      onClick={handleSync}
      title={message}
      type="button"
    >
      {label}
    </button>
  );
}
