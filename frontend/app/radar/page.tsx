import type { Metadata } from 'next';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { RadarDashboard } from '@/components/radar/radar-dashboard';
import { getRadarItems } from '@/lib/api';

export const metadata: Metadata = {
  title: 'AI 前沿研究雷达',
  description: '聚合论文、模型与开源项目；当前本地版本使用清楚标记的演示数据。',
};

export default async function RadarPage() {
  const items = await getRadarItems();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/radar" action="api" />
      <div className="site-shell py-6">
        <div className="mb-4 grid gap-5 lg:grid-cols-[1fr_1.15fr] lg:items-center">
          <header>
            <h1 className="text-[clamp(2.1rem,3.3vw,3rem)] font-black tracking-tight"><span className="text-brand">AI 前沿</span> · 每日研究雷达</h1>
            <p className="mt-1 text-sm text-muted-ink">聚合论文、模型与开源项目，追踪大模型推理优化的最新进展。</p>
          </header>
          <section className="stats-banner" aria-label="本地雷达状态">
            <div><span>本地演示条目</span><strong>{items.length}</strong></div>
            <div><span>真实数据源</span><strong>0</strong></div>
            <div className="flex-1"><span>更新状态</span><p className="mt-2 text-base">等待后台配置</p></div>
            <button className="primary-action opacity-60" disabled title="仅允许通过 Django 管理命令同步" type="button">仅后台同步 ↻</button>
          </section>
        </div>

        <RadarDashboard initialItems={items} />
      </div>
      <SiteFooter />
    </main>
  );
}
