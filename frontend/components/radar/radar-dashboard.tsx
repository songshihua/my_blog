'use client';

import { useMemo, useState } from 'react';

import { SiteIcon } from '@/components/ui/site-icon';
import { RadarBriefButton } from '@/components/radar/radar-brief-button';
import { Spinner } from '@/components/ui/spinner';
import {
  RadarItemSummaryRequestError,
  summarizeRadarItem,
} from '@/lib/api';
import type { RadarItem, RadarSource, RadarStats } from '@/lib/site-data';

const PAGE_SIZE = 10;

const sourcePresentation: Record<string, { mark: string; className: string }> =
  {
    arxiv: { mark: 'arXiv', className: 'bg-[#b8232b]' },
    huggingface: { mark: 'HF', className: 'bg-[#ffcf3e] text-black' },
    github: { mark: 'GH', className: 'bg-black' },
  };

const statusDot: Record<RadarSource['status'], string> = {
  success: 'bg-success',
  running: 'bg-brand',
  error: 'bg-orange-500',
  idle: 'bg-amber-400',
  disabled: 'bg-slate-400',
};

const topics = [
  '全部',
  '推理优化',
  'Speculative Decoding',
  'KV Cache',
  'Quantization',
  'LLM Serving',
];

function formatTimestamp(value: string) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return '时间未知';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(timestamp);
}

function sourceStatus(source: RadarSource) {
  if (!source.is_configured) return '未配置';
  if (source.status === 'success' && source.last_success_at) {
    return `${source.is_enabled ? '正常' : '已同步 · 手动模式'} · ${formatTimestamp(source.last_success_at)}`;
  }
  if (!source.is_enabled) return '已配置 · 手动模式';
  return source.status_label;
}

type OverviewRow = {
  icon: string;
  kind: string;
  label: string;
  value: number;
};
type PageToken = number | `ellipsis-${number}`;

function getPageTokens(activePage: number, totalPages: number): PageToken[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages]);
  for (let page = activePage - 1; page <= activePage + 1; page += 1) {
    if (page > 1 && page < totalPages) pages.add(page);
  }
  if (activePage <= 4) {
    for (let page = 2; page <= 5; page += 1) pages.add(page);
  }
  if (activePage >= totalPages - 3) {
    for (let page = totalPages - 4; page < totalPages; page += 1)
      pages.add(page);
  }

  const sortedPages = [...pages].sort((left, right) => left - right);
  return sortedPages.flatMap<PageToken>((page, index) => {
    const previousPage = sortedPages[index - 1];
    return index > 0 && page - previousPage > 1
      ? [`ellipsis-${previousPage}`, page]
      : [page];
  });
}

export function RadarDashboard({
  initialItems,
  sources,
  stats,
}: {
  initialItems: RadarItem[];
  sources: RadarSource[];
  stats: RadarStats;
}) {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [kind, setKind] = useState('all');
  const [topic, setTopic] = useState('全部');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(
    initialItems.find((item) => !item.is_demo)?.id ?? null,
  );
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [itemSummaries, setItemSummaries] = useState<
    Record<number, Record<string, string>>
  >(() =>
    Object.fromEntries(
      initialItems
        .filter(
          (item) => item.ai_summary && Object.keys(item.ai_summary).length,
        )
        .map((item) => [item.id, item.ai_summary ?? {}]),
    ),
  );
  const [summarizingIds, setSummarizingIds] = useState<number[]>([]);
  const [summaryErrors, setSummaryErrors] = useState<Record<number, string>>(
    {},
  );

  const liveItems = useMemo(
    () =>
      initialItems
        .filter((item) => !item.is_demo)
        .map((item) => ({
          ...item,
          ai_summary: itemSummaries[item.id] ?? item.ai_summary,
        })),
    [initialItems, itemSummaries],
  );

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return liveItems.filter((item) => {
      const matchesQuery =
        !normalized ||
        `${item.title} ${item.summary} ${item.authors.join(' ')}`
          .toLowerCase()
          .includes(normalized);
      const matchesSource =
        source === 'all' || item.source.source_type === source;
      const matchesKind = kind === 'all' || item.kind === kind;
      const matchesTopic =
        topic === '全部' ||
        item.topics.some((entry) => entry.name === topic) ||
        (topic === '推理优化' && item.topics.length > 0);
      return matchesQuery && matchesSource && matchesKind && matchesTopic;
    });
  }, [kind, liveItems, query, source, topic]);

  const totalPages = Math.ceil(visibleItems.length / PAGE_SIZE);
  const activePage = Math.min(currentPage, Math.max(totalPages, 1));
  const pageTokens = useMemo(
    () => getPageTokens(activePage, totalPages),
    [activePage, totalPages],
  );
  const paginatedItems = useMemo(() => {
    const start = (activePage - 1) * PAGE_SIZE;
    return visibleItems.slice(start, start + PAGE_SIZE);
  }, [activePage, visibleItems]);

  const trendingTopics = useMemo(() => {
    const counts = new Map<string, number>();
    liveItems.forEach((item) =>
      item.topics.forEach((entry) =>
        counts.set(entry.name, (counts.get(entry.name) ?? 0) + 1),
      ),
    );
    return [...counts.entries()]
      .sort((left, right) => right[1] - left[1])
      .slice(0, 5);
  }, [liveItems]);

  const overview: OverviewRow[] = [
    {
      icon: '▣',
      kind: 'paper',
      label: '新增论文',
      value: stats.by_kind.paper ?? 0,
    },
    {
      icon: '⌘',
      kind: 'repository',
      label: '开源项目',
      value: stats.by_kind.repository ?? 0,
    },
    {
      icon: '◇',
      kind: 'model',
      label: '模型发布',
      value: stats.by_kind.model ?? 0,
    },
    {
      icon: '▤',
      kind: 'dataset',
      label: '数据集',
      value: stats.by_kind.dataset ?? 0,
    },
  ];
  function toggleSaved(id: number) {
    setSavedIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }

  async function toggleItemSummary(item: RadarItem) {
    const hasSummary = Boolean(
      item.ai_summary && Object.keys(item.ai_summary).length,
    );
    if (hasSummary) {
      setExpandedId(item.id === expandedId ? null : item.id);
      return;
    }
    if (summarizingIds.includes(item.id)) return;

    setSummarizingIds((current) => [...current, item.id]);
    setSummaryErrors((current) => ({ ...current, [item.id]: '' }));
    try {
      const result = await summarizeRadarItem(item.id);
      setItemSummaries((current) => ({
        ...current,
        [item.id]: result.ai_summary,
      }));
      setExpandedId(item.id);
    } catch (cause) {
      setSummaryErrors((current) => ({
        ...current,
        [item.id]:
          cause instanceof RadarItemSummaryRequestError
            ? cause.message
            : '内容总结失败，请稍后重试。',
      }));
    } finally {
      setSummarizingIds((current) =>
        current.filter((itemId) => itemId !== item.id),
      );
    }
  }

  function filterByKind(nextKind: string) {
    setKind((current) => (current === nextKind ? 'all' : nextKind));
    setCurrentPage(1);
    window.requestAnimationFrame(() =>
      document
        .getElementById('radar-results')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
    );
  }

  return (
    <>
      <section className="grid gap-3 md:grid-cols-3" aria-label="数据源状态">
        {sources.map((item) => {
          const presentation = sourcePresentation[item.source_type] ?? {
            mark: item.name.slice(0, 2),
            className: 'bg-slate-700',
          };
          return (
            <a
              className="source-status-card"
              href={item.homepage_url}
              key={item.source_type}
              rel="noreferrer"
              target="_blank"
            >
              <span className={`source-mark ${presentation.className}`}>
                {presentation.mark}
              </span>
              <div className="min-w-0">
                <h2 className="truncate font-semibold">{item.name}</h2>
                <p className="mt-1 flex items-center gap-2 text-[11px] text-muted-ink">
                  <span
                    className={`size-2 shrink-0 rounded-full ${statusDot[item.status]}`}
                  />
                  <span className="truncate">{sourceStatus(item)}</span>
                </p>
              </div>
            </a>
          );
        })}
      </section>

      <div className="mt-4 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_375px]">
        <div>
          <section className="filter-panel" aria-label="研究雷达搜索与筛选">
            <div className="flex gap-3">
              <label className="search-shell flex-1">
                <SiteIcon
                  className="size-5 text-muted-foreground"
                  name="search"
                />
                <span className="sr-only">搜索论文、模型、作者或关键词</span>
                <input
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="搜索论文、模型、作者或关键词"
                  value={query}
                />
              </label>
              <button className="primary-action w-32" type="button">
                搜索
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-3 border-b border-line pb-3">
              <select
                aria-label="全部来源"
                className="select-control"
                onChange={(event) => {
                  setSource(event.target.value);
                  setCurrentPage(1);
                }}
                value={source}
              >
                <option value="all">全部来源</option>
                {sources.map((item) => (
                  <option key={item.source_type} value={item.source_type}>
                    {item.name}
                  </option>
                ))}
              </select>
              <select
                aria-label="发布时间"
                className="select-control"
                defaultValue="all"
              >
                <option value="all">全部时间</option>
                <option value="24h">最近 24 小时</option>
                <option value="7d">最近 7 天</option>
              </select>
              <select
                aria-label="排序方式"
                className="select-control"
                defaultValue="latest"
              >
                <option value="latest">按时间排序</option>
                <option value="relevance">按相关度排序</option>
              </select>
            </div>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {topics.map((item) => (
                <button
                  className={`topic-tab ${topic === item ? 'topic-tab-active' : ''}`}
                  key={item}
                  onClick={() => {
                    setTopic(item);
                    setCurrentPage(1);
                  }}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </section>

          <div
            className="mb-2 mt-3 scroll-mt-20 flex items-end justify-between px-1"
            id="radar-results"
          >
            <h2 className="text-lg font-black">
              研究更新{' '}
              <span className="ml-2 text-xs font-normal text-muted-ink">
                {visibleItems.length} 条结果
              </span>
            </h2>
            <span className="text-xs text-muted-ink">
              真实来源 {liveItems.length} 条
            </span>
          </div>

          <div className="space-y-2">
            {paginatedItems.length ? (
              paginatedItems.map((item) => {
                const expanded = item.id === expandedId;
                const saved = savedIds.includes(item.id);
                const summarizing = summarizingIds.includes(item.id);
                const hasAiSummary = Boolean(
                  item.ai_summary && Object.keys(item.ai_summary).length,
                );
                const presentation = sourcePresentation[
                  item.source.source_type
                ] ?? {
                  mark: item.source.name.slice(0, 8),
                  className: 'bg-slate-700',
                };
                return (
                  <article
                    className={`feed-card ${expanded ? 'feed-card-expanded' : ''}`}
                    key={item.id}
                  >
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-ink">
                      <span
                        className={`rounded px-1.5 py-0.5 font-bold text-white ${presentation.className}`}
                      >
                        {presentation.mark}
                      </span>
                      <span>·</span>
                      <span>{formatTimestamp(item.published_at)}</span>
                      <span className="tag-chip ml-1 text-success">LIVE</span>
                      <div className="ml-auto flex gap-2">
                        <button
                          aria-busy={summarizing}
                          className="small-action text-brand disabled:cursor-wait disabled:opacity-60"
                          disabled={summarizing}
                          onClick={() => toggleItemSummary(item)}
                          type="button"
                        >
                          {summarizing ? (
                            <Spinner />
                          ) : (
                            <SiteIcon name="sparkle" />
                          )}{' '}
                          {summarizing
                            ? '总结中…'
                            : hasAiSummary
                              ? 'AI 摘要'
                              : 'AI 总结'}
                        </button>
                        <button
                          aria-pressed={saved}
                          className="small-action"
                          onClick={() => toggleSaved(item.id)}
                          type="button"
                        >
                          <SiteIcon name="bookmark" />{' '}
                          {saved ? '已收藏' : '收藏'}
                        </button>
                        <a
                          className="small-action"
                          href={item.original_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          查看原文 <SiteIcon name="arrow" />
                        </a>
                      </div>
                    </div>
                    <button
                      className="mt-2 block w-full text-left"
                      onClick={() =>
                        hasAiSummary && setExpandedId(expanded ? null : item.id)
                      }
                      type="button"
                    >
                      <h3 className="text-lg font-black tracking-tight">
                        {item.title}
                      </h3>
                      <p className="mt-1 text-xs leading-6 text-muted-ink">
                        {item.summary || '该来源未提供摘要，请查看原文。'}
                      </p>
                    </button>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-ink">
                      {item.authors.length > 0 && (
                        <span>作者：{item.authors.join(', ')}</span>
                      )}
                      {item.repository_metrics && (
                        <span className="tag-chip text-brand">
                          ★ {item.repository_metrics.stars}
                        </span>
                      )}
                      {item.repository_metrics?.language && (
                        <span className="tag-chip">
                          {item.repository_metrics.language}
                        </span>
                      )}
                      {item.repository_metrics && (
                        <span className="tag-chip">
                          Fork {item.repository_metrics.forks}
                        </span>
                      )}
                      <span className="tag-chip">{item.kind_label}</span>
                      {item.topics.map((entry) => (
                        <span className="tag-chip" key={entry.slug}>
                          {entry.name}
                        </span>
                      ))}
                    </div>
                    {expanded && hasAiSummary && (
                      <dl className="ai-summary-panel mt-3">
                        {Object.entries(item.ai_summary ?? {}).map(
                          ([label, value]) => (
                            <div key={label}>
                              <dt>{label}</dt>
                              <dd>{value}</dd>
                            </div>
                          ),
                        )}
                      </dl>
                    )}
                    {summaryErrors[item.id] && (
                      <p
                        aria-live="polite"
                        className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
                      >
                        {summaryErrors[item.id]}
                      </p>
                    )}
                  </article>
                );
              })
            ) : (
              <div className="empty-state">
                暂无真实研究内容，请先同步数据源或调整筛选条件。
              </div>
            )}
          </div>

          {visibleItems.length > 0 && (
            <nav
              aria-label="研究更新分页"
              className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-white/75 px-4 py-3"
            >
              <p aria-live="polite" className="text-xs text-muted-ink">
                第 {(activePage - 1) * PAGE_SIZE + 1}–
                {Math.min(activePage * PAGE_SIZE, visibleItems.length)} 条，共{' '}
                {visibleItems.length} 条
              </p>
              <div className="flex flex-wrap items-center justify-end gap-1">
                <button
                  aria-label="上一页"
                  className="min-h-9 rounded-lg border border-line bg-white px-3 text-xs font-semibold transition-colors hover:border-brand hover:text-brand disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={activePage === 1}
                  onClick={() => setCurrentPage(activePage - 1)}
                  type="button"
                >
                  上一页
                </button>
                {pageTokens.map((page) =>
                  typeof page === 'number' ? (
                    <button
                      aria-current={page === activePage ? 'page' : undefined}
                      aria-label={`第 ${page} 页`}
                      className={`grid size-9 place-items-center rounded-lg border text-xs font-bold transition-colors ${
                        page === activePage
                          ? 'border-brand bg-brand text-white'
                          : 'border-line bg-white hover:border-brand hover:text-brand'
                      }`}
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      type="button"
                    >
                      {page}
                    </button>
                  ) : (
                    <span
                      aria-hidden="true"
                      className="grid size-9 place-items-center text-xs text-muted-ink"
                      key={page}
                    >
                      …
                    </span>
                  ),
                )}
                <button
                  aria-label="下一页"
                  className="min-h-9 rounded-lg border border-line bg-white px-3 text-xs font-semibold transition-colors hover:border-brand hover:text-brand disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={activePage === totalPages}
                  onClick={() => setCurrentPage(activePage + 1)}
                  type="button"
                >
                  下一页
                </button>
              </div>
            </nav>
          )}
        </div>

        <aside className="space-y-3 xl:sticky xl:top-20">
          <section className="side-card">
            <h2>内容速览</h2>
            {overview.map(({ icon, kind: rowKind, label, value }) => (
              <button
                aria-pressed={kind === rowKind}
                className={`overview-row w-full text-left transition-colors hover:text-brand ${
                  kind === rowKind ? 'overview-row-active' : ''
                }`}
                key={label}
                onClick={() => filterByKind(rowKind)}
                type="button"
              >
                <span className="text-brand">{icon}</span>
                <span>{label}</span>
                <strong>{value}</strong>
                <span>›</span>
              </button>
            ))}
          </section>
          <section className="side-card">
            <h2>趋势关键词</h2>
            {trendingTopics.length ? (
              trendingTopics.map(([keyword, count], index) => (
                <div className="trend-row" key={keyword}>
                  <span>{index + 1}</span>
                  <span className="flex-1">{keyword}</span>
                  <span className="text-success">{count} 条</span>
                </div>
              ))
            ) : (
              <p className="py-4 text-xs text-muted-ink">
                同步真实来源后自动统计。
              </p>
            )}
            <p className="mt-3 text-center text-[11px] text-muted-ink">
              基于当前公开条目的主题统计
            </p>
          </section>
          <section className="side-card">
            <h2>
              已收藏 <span className="text-brand">{savedIds.length}</span>
            </h2>
            {savedIds.length ? (
              liveItems
                .filter((item) => savedIds.includes(item.id))
                .map((item) => (
                  <p
                    className="border-b border-line py-2 text-xs"
                    key={item.id}
                  >
                    {item.title}
                  </p>
                ))
            ) : (
              <p className="py-4 text-xs text-muted-ink">
                收藏仅保留在当前页面会话中。
              </p>
            )}
          </section>
          <RadarBriefButton />
        </aside>
      </div>
    </>
  );
}
