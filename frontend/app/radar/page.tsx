import type { Metadata } from 'next';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { RadarDashboard } from '@/components/radar/radar-dashboard';
import { RadarSyncButton } from '@/components/radar/radar-sync-button';
import { getRadarItems, getRadarSources, getRadarStats } from '@/lib/api';

export const metadata: Metadata = {
  title: 'AI 前沿研究雷达',
  description: '聚合 arXiv、GitHub 与 Hugging Face 的 AI 研究进展。',
};

export default async function RadarPage() {
  const [items, sources, stats] = await Promise.all([
    getRadarItems(),
    getRadarSources(),
    getRadarStats(),
  ]);
  // 当前界面仅展示三个主要来源；隐藏项仍保留后端兼容性，便于以后按需恢复。
  const visibleSources = sources.filter(
    (source) => source.source_type !== 'openreview' && source.source_type !== 'deepseek',
  );
  const liveSources = visibleSources.filter((source) => source.status === 'success').length;
  const lastUpdated = stats.last_success_at
    ? new Intl.DateTimeFormat('zh-CN', {
        dateStyle: 'short',
        timeStyle: 'short',
        timeZone: 'Asia/Shanghai',
      }).format(new Date(stats.last_success_at))
    : '等待首次同步';

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/radar" action="api" />
      <div className="site-shell py-6">
        <div className="mb-4 grid gap-5 lg:grid-cols-[1fr_1.15fr] lg:items-center">
          <header>
            <h1 className="text-[clamp(2.1rem,3.3vw,3rem)] font-black tracking-tight"><span className="text-brand">AI 前沿</span> · 每日研究雷达</h1>
            <p className="mt-1 text-sm text-muted-ink">聚合论文、模型与开源项目，追踪大模型推理优化的最新进展。</p>
          </header>
          <section className="stats-banner" aria-label="研究雷达状态">
            <div><span>今日新增</span><strong>{stats.today_count}</strong></div>
            <div><span>正常数据源</span><strong>{liveSources}</strong></div>
            <div className="flex-1"><span>最近同步</span><p className="mt-2 text-base">{lastUpdated}</p></div>
            <RadarSyncButton />
          </section>
        </div>

        <RadarDashboard initialItems={items} sources={visibleSources} stats={stats} />
      </div>
      <SiteFooter />
    </main>
  );
}
