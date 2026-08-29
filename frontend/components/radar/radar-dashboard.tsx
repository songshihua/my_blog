'use client';

import { useMemo, useState } from 'react';

import { SiteIcon } from '@/components/ui/site-icon';
import type { RadarItem } from '@/lib/site-data';

const sources = [
  { value: 'arxiv', name: 'arXiv API', mark: 'arXiv', className: 'bg-[#b8232b]' },
  { value: 'huggingface', name: 'Hugging Face', mark: 'HF', className: 'bg-[#ffcf3e] text-black' },
  { value: 'github', name: 'GitHub Trending', mark: 'GH', className: 'bg-black' },
  { value: 'openreview', name: 'OpenReview', mark: 'OR', className: 'bg-[#a73a2e]' },
];

const topics = ['全部', '推理优化', 'Speculative Decoding', 'KV Cache', 'Quantization', 'LLM Serving'];

export function RadarDashboard({ initialItems }: { initialItems: RadarItem[] }) {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [topic, setTopic] = useState('全部');
  const [expandedId, setExpandedId] = useState<number | null>(initialItems[0]?.id ?? null);
  const [savedIds, setSavedIds] = useState<number[]>([]);

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return initialItems.filter((item) => {
      const matchesQuery = !normalized || `${item.title} ${item.summary} ${item.authors.join(' ')}`.toLowerCase().includes(normalized);
      const matchesSource = source === 'all' || item.source.source_type === source;
      const matchesTopic = topic === '全部' || item.topics.some((entry) => entry.name === topic) || (topic === '推理优化' && item.topics.length > 0);
      return matchesQuery && matchesSource && matchesTopic;
    });
  }, [initialItems, query, source, topic]);

  function toggleSaved(id: number) {
    setSavedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  return (
    <>
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4" aria-label="数据源状态">
        {sources.map((item) => (
          <article className="source-status-card" key={item.value}>
            <span className={`source-mark ${item.className}`}>{item.mark}</span>
            <div><h2 className="font-semibold">{item.name}</h2><p className="mt-1 flex items-center gap-2 text-[11px] text-muted-ink"><span className="size-2 rounded-full bg-slate-400" />未配置 · 本地演示</p></div>
          </article>
        ))}
      </section>

      <div className="mt-4 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_375px]">
        <div>
          <section className="filter-panel" aria-label="研究雷达搜索与筛选">
            <div className="flex gap-3">
              <label className="search-shell flex-1">
                <SiteIcon className="size-5 text-muted-foreground" name="search" />
                <span className="sr-only">搜索论文、模型、作者或关键词</span>
                <input onChange={(event) => setQuery(event.target.value)} placeholder="搜索论文、模型、作者或关键词" value={query} />
              </label>
              <button className="primary-action w-32" type="button">搜索</button>
            </div>
            <div className="mt-2 flex flex-wrap gap-3 border-b border-line pb-3">
              <select aria-label="全部来源" className="select-control" onChange={(event) => setSource(event.target.value)} value={source}>
                <option value="all">全部来源</option>
                {sources.map((item) => <option key={item.value} value={item.value}>{item.name}</option>)}
              </select>
              <select aria-label="发布时间" className="select-control" defaultValue="24h"><option value="24h">最近 24 小时</option><option value="7d">最近 7 天</option></select>
              <select aria-label="排序方式" className="select-control" defaultValue="relevance"><option value="relevance">按相关度排序</option><option value="latest">按时间排序</option></select>
            </div>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {topics.map((item) => <button className={`topic-tab ${topic === item ? 'topic-tab-active' : ''}`} key={item} onClick={() => setTopic(item)} type="button">{item}</button>)}
            </div>
          </section>

          <div className="mb-2 mt-3 flex items-end justify-between px-1">
            <h2 className="text-lg font-black">今日更新 <span className="ml-2 text-xs font-normal text-muted-ink">{visibleItems.length} 条演示结果</span></h2>
            <span className="text-xs text-muted-ink">界面示例 · 数据为演示内容</span>
          </div>

          <div className="space-y-2">
            {visibleItems.length ? visibleItems.map((item) => {
              const expanded = item.id === expandedId;
              const saved = savedIds.includes(item.id);
              return (
                <article className={`feed-card ${expanded ? 'feed-card-expanded' : ''}`} key={item.id}>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-ink">
                    <span className="rounded bg-red-600 px-1.5 py-0.5 font-bold text-white">{item.source.name.slice(0, 8)}</span>
                    <span>·</span><span>{Math.max(1, new Date().getHours() - new Date(item.published_at).getHours())} 小时前</span>
                    <span className="demo-badge ml-1">SAMPLE</span>
                    <div className="ml-auto flex gap-2">
                      <button className="small-action text-brand" onClick={() => setExpandedId(expanded ? null : item.id)} type="button"><SiteIcon name="sparkle" /> AI 摘要</button>
                      <button aria-pressed={saved} className="small-action" onClick={() => toggleSaved(item.id)} type="button"><SiteIcon name="bookmark" /> {saved ? '已收藏' : '收藏'}</button>
                      <a className="small-action" href={item.original_url} rel="noreferrer" target="_blank">查看原文 <SiteIcon name="arrow" /></a>
                    </div>
                  </div>
                  <button className="mt-2 block w-full text-left" onClick={() => setExpandedId(expanded ? null : item.id)} type="button">
                    <h3 className="text-lg font-black tracking-tight">{item.title}</h3>
                    <p className="mt-1 text-xs leading-6 text-muted-ink">{item.summary}</p>
                  </button>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-ink"><span>作者：{item.authors.join(', ')}</span>{item.topics.map((entry) => <span className="tag-chip" key={entry.slug}>{entry.name}</span>)}</div>
                  {expanded && item.ai_summary && (
                    <dl className="ai-summary-panel mt-3">
                      {Object.entries(item.ai_summary).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
                    </dl>
                  )}
                </article>
              );
            }) : <div className="empty-state">没有符合当前条件的演示内容。</div>}
          </div>
        </div>

        <aside className="space-y-3 xl:sticky xl:top-20">
          <section className="side-card">
            <h2>今日速览</h2>
            {[['▣', '新增论文', initialItems.filter((item) => item.kind === 'paper').length], ['⌘', '开源项目', initialItems.filter((item) => item.kind === 'repository').length], ['◇', '模型发布', initialItems.filter((item) => item.kind === 'model').length]].map(([icon, label, value]) => <div className="overview-row" key={String(label)}><span className="text-brand">{icon}</span><span>{label}</span><strong>{value}</strong><span>›</span></div>)}
          </section>
          <section className="side-card">
            <h2>趋势关键词</h2>
            {['Speculative Decoding', 'KV Cache', 'Long Context', 'Continuous Batching', 'Quantization'].map((keyword, index) => <div className="trend-row" key={keyword}><span>{index + 1}</span><span className="flex-1">{keyword}</span><span className="text-success">演示</span></div>)}
            <p className="mt-3 text-center text-[11px] text-muted-ink">接入真实来源后计算趋势</p>
          </section>
          <section className="side-card">
            <h2>已收藏 <span className="text-brand">{savedIds.length}</span></h2>
            {savedIds.length ? initialItems.filter((item) => savedIds.includes(item.id)).map((item) => <p className="border-b border-line py-2 text-xs" key={item.id}>{item.title}</p>) : <p className="py-4 text-xs text-muted-ink">收藏仅保留在当前页面会话中。</p>}
          </section>
          <button className="secondary-action w-full" disabled title="生成服务将在配置后端任务后启用" type="button"><SiteIcon name="document" /> 生成今日简报（待配置）</button>
        </aside>
      </div>
    </>
  );
}
