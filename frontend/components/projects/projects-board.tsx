'use client';

import { useMemo, useState } from 'react';

import { SiteIcon } from '@/components/ui/site-icon';
import {
  KvCacheMatrix,
  PerformanceChart,
  ServingTopology,
  SpeculativePipeline,
} from '@/components/visuals/research-diagrams';
import type { Project } from '@/lib/site-data';

const filters = [
  { value: 'all', label: '全部' },
  { value: 'inference', label: '推理优化' },
  { value: 'system', label: '系统实践' },
  { value: 'tool', label: '工具' },
  { value: 'learning', label: '学习实验' },
];

function formatSyncTime(value?: string | null) {
  if (!value) return '尚未记录';
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return '时间未知';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(timestamp);
}

function ProjectTags({ project }: { project: Project }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {project.topics.map((topic) => <span className="tag-chip" key={topic.slug}>{topic.name}</span>)}
      {!project.is_demo && project.source_metadata?.language && <span className="tag-chip">{project.source_metadata.language}</span>}
      {!project.is_demo && project.source_metadata?.license && <span className="tag-chip">{project.source_metadata.license}</span>}
    </div>
  );
}

function RepositoryFacts({ project }: { project: Project }) {
  const metadata = project.source_metadata ?? {};
  const facts = [
    ['语言', metadata.language || '未标注'],
    ['Stars', String(metadata.stars ?? 0)],
    ['Forks', String(metadata.forks ?? 0)],
    ['Issues', String(metadata.open_issues ?? 0)],
    ['默认分支', metadata.default_branch || '未标注'],
    ['许可证', metadata.license || '未标注'],
  ];
  return (
    <dl className="grid grid-cols-2 gap-2 text-xs">
      {facts.map(([label, value]) => (
        <div className="rounded-lg border border-line bg-white/75 p-3" key={label}>
          <dt className="text-muted-ink">{label}</dt>
          <dd className="mt-1 truncate font-bold">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ProjectBadge({ project }: { project: Project }) {
  if (project.is_demo) return <span className="demo-badge">概念项目 / DEMO</span>;
  if (project.external_source === 'github') return <span className="tag-chip text-success">GitHub 同步 / LIVE</span>;
  return <span className="tag-chip text-success">正式项目</span>;
}

export function ProjectsBoard({ projects }: { projects: Project[] }) {
  const [active, setActive] = useState('all');
  const visible = useMemo(
    () => (active === 'all' ? projects : projects.filter((project) => project.category === active)),
    [active, projects],
  );
  const featured = visible[0];
  const rest = visible.slice(1);

  return (
    <>
      <div aria-label="项目分类" className="mb-3 flex flex-wrap gap-3">
        {filters.map((filter) => (
          <button
            aria-pressed={active === filter.value}
            className={`filter-chip ${active === filter.value ? 'filter-chip-active' : ''}`}
            key={filter.value}
            onClick={() => setActive(filter.value)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {featured ? featured.is_demo ? (
        <section className="project-feature" aria-label={featured.title}>
          <div className="project-copy">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-black tracking-tight">{featured.title}</h2>
              <ProjectBadge project={featured} />
            </div>
            <p className="mt-1 text-sm font-medium">{featured.subtitle}</p>
            <dl className="mt-5 space-y-4 text-xs leading-6">
              <div><dt className="font-bold">研究问题</dt><dd className="text-muted-ink">{featured.problem}</dd></div>
              <div><dt className="font-bold">设计思路</dt><dd className="text-muted-ink">{featured.approach}</dd></div>
            </dl>
            <ProjectTags project={featured} />
            <a className="primary-action mt-4 h-10" href={featured.repository_url} rel="noreferrer" target="_blank">
              查看案例 <SiteIcon name="arrow" />
            </a>
          </div>
          <div className="project-visual border-l border-line p-6">
            <h3 className="mb-2 text-xs font-bold">投机解码流水线（概念示意）</h3>
            <SpeculativePipeline />
          </div>
          <div className="project-visual border-l border-line p-6">
            <h3 className="mb-2 text-center text-xs font-bold">延迟-吞吐示意曲线</h3>
            <PerformanceChart />
            <p className="text-center text-[10px] text-muted-ink">Illustrative data / 示意数据</p>
          </div>
        </section>
      ) : (
        <section className="project-feature" aria-label={featured.title}>
          <div className="project-copy">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-black tracking-tight">{featured.title}</h2>
              <ProjectBadge project={featured} />
            </div>
            <p className="mt-1 text-sm font-medium">{featured.subtitle}</p>
            <p className="mt-5 text-xs leading-6 text-muted-ink">{featured.summary || '该仓库暂未提供简介。'}</p>
            <ProjectTags project={featured} />
            {featured.repository_url && <a className="primary-action mt-4 h-10" href={featured.repository_url} rel="noreferrer" target="_blank">查看仓库 <SiteIcon name="external" /></a>}
          </div>
          <div className="project-visual border-l border-line p-6">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-brand">Repository Metadata</p>
            <h3 className="mt-2 text-lg font-black">{featured.source_metadata?.full_name || featured.title}</h3>
            <p className="mt-3 text-xs leading-6 text-muted-ink">数据来自 GitHub 官方 API；这里只展示仓库公开元数据，不生成虚假的实验结论或性能曲线。</p>
            <p className="mt-5 text-[11px] text-muted-ink">最后同步：{formatSyncTime(featured.last_synced_at)}</p>
          </div>
          <div className="project-visual border-l border-line p-6">
            <RepositoryFacts project={featured} />
          </div>
        </section>
      ) : (
        <div className="empty-state">该分类暂时没有公开项目。</div>
      )}

      {rest.length > 0 && (
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {rest.map((project) => (
            <article className="project-secondary" key={project.slug}>
              <div className="w-full lg:w-[48%]">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-xl font-black">{project.title}</h2>
                  <ProjectBadge project={project} />
                </div>
                <p className="mt-1 text-sm font-semibold">{project.subtitle}</p>
                {project.is_demo ? (
                  <dl className="mt-4 space-y-3 text-xs leading-6">
                    <div><dt className="font-bold">研究问题</dt><dd className="text-muted-ink">{project.problem}</dd></div>
                    <div><dt className="font-bold">设计思路</dt><dd className="text-muted-ink">{project.approach}</dd></div>
                  </dl>
                ) : <p className="mt-4 text-xs leading-6 text-muted-ink">{project.summary || '该仓库暂未提供简介。'}</p>}
                <ProjectTags project={project} />
                {!project.is_demo && project.repository_url && <a className="secondary-action mt-4 h-9" href={project.repository_url} rel="noreferrer" target="_blank">查看仓库 <SiteIcon name="external" /></a>}
              </div>
              <div className="min-w-0 flex-1">
                {project.is_demo ? (
                  project.category === 'system' ? <><KvCacheMatrix /><div className="memory-timeline"><span /><span /><span /></div></> : <ServingTopology />
                ) : <><RepositoryFacts project={project} /><p className="mt-3 text-[11px] text-muted-ink">最后同步：{formatSyncTime(project.last_synced_at)}</p></>}
              </div>
            </article>
          ))}
        </div>
      )}

      <section className="workflow-strip mt-3" aria-labelledby="workflow-heading">
        <h2 className="shrink-0 text-lg font-black" id="workflow-heading">我的研究工作流</h2>
        {[
          ['1', '问题定义', '明确研究目标与约束'],
          ['2', '文献调研', '梳理相关工作与方法'],
          ['3', '实验设计', '方案设计与基线设定'],
          ['4', '性能分析', '实验评估与瓶颈定位'],
          ['5', '复盘沉淀', '总结经验与知识记录'],
        ].map(([number, title, description], index) => (
          <div className="workflow-step" key={number}>
            <span>{number}</span>
            <div><h3>{title}</h3><p>{description}</p></div>
            {index < 4 && <b aria-hidden="true">→</b>}
          </div>
        ))}
      </section>
    </>
  );
}
