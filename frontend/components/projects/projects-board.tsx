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

      {featured ? (
        <section className="project-feature" aria-label={featured.title}>
          <div className="project-copy">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-black tracking-tight">{featured.title}</h2>
              {featured.is_demo && <span className="demo-badge">概念项目 / DEMO</span>}
            </div>
            <p className="mt-1 text-sm font-medium">{featured.subtitle}</p>
            <dl className="mt-5 space-y-4 text-xs leading-6">
              <div><dt className="font-bold">研究问题</dt><dd className="text-muted-ink">{featured.problem}</dd></div>
              <div><dt className="font-bold">设计思路</dt><dd className="text-muted-ink">{featured.approach}</dd></div>
            </dl>
            <div className="mt-3 flex flex-wrap gap-2">
              {featured.topics.map((topic) => <span className="tag-chip" key={topic.slug}>{topic.name}</span>)}
            </div>
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
        <div className="empty-state">该分类暂时没有公开项目。</div>
      )}

      {rest.length > 0 && (
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {rest.map((project) => (
            <article className="project-secondary" key={project.slug}>
              <div className="w-full lg:w-[43%]">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-black">{project.title}</h2>
                </div>
                <p className="mt-1 text-sm font-semibold">{project.subtitle}</p>
                <dl className="mt-4 space-y-3 text-xs leading-6">
                  <div><dt className="font-bold">研究问题</dt><dd className="text-muted-ink">{project.problem}</dd></div>
                  <div><dt className="font-bold">设计思路</dt><dd className="text-muted-ink">{project.approach}</dd></div>
                </dl>
                <div className="mt-3 flex flex-wrap gap-2">{project.topics.map((topic) => <span className="tag-chip" key={topic.slug}>{topic.name}</span>)}</div>
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex justify-end"><span className="demo-badge">概念项目 / DEMO</span></div>
                {project.category === 'system' ? <><KvCacheMatrix /><div className="memory-timeline"><span /><span /><span /></div></> : <ServingTopology />}
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
