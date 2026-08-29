import type { Metadata } from 'next';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { ProjectsBoard } from '@/components/projects/projects-board';
import { SiteIcon } from '@/components/ui/site-icon';
import { getProjects } from '@/lib/api';

export const metadata: Metadata = {
  title: '项目与研究实践',
  description: '围绕大模型推理优化的概念项目、实验记录与工程实践。',
};

export default async function ProjectsPage() {
  const projects = await getProjects();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/projects" />
      <div className="site-shell py-7">
        <header className="mb-4">
          <h1 className="text-[clamp(2rem,3vw,2.7rem)] font-black tracking-tight">项目与研究实践</h1>
          <p className="mt-1 text-sm text-muted-ink">围绕大模型推理优化，记录问题、实验与工程思考。</p>
          <p className="mt-2 text-[11px] font-bold uppercase tracking-[0.12em] text-brand">Research Portfolio</p>
        </header>

        <ProjectsBoard projects={projects} />

        <section className="github-banner mt-3">
          <SiteIcon className="size-9 text-brand" name="code" />
          <div className="min-w-0 flex-1"><h2 className="text-xl font-black text-brand">更多代码与学习记录</h2><p className="mt-1 text-xs text-muted-ink">所有概念项目的代码、实验记录与学习笔记持续更新中。</p></div>
          <a className="primary-action" href="https://github.com/songshihua/" rel="noreferrer" target="_blank">访问 GitHub <SiteIcon name="arrow" /></a>
          <a className="text-base font-semibold text-brand" href="https://github.com/songshihua/" rel="noreferrer" target="_blank">github.com/songshihua</a>
        </section>
      </div>
      <SiteFooter />
    </main>
  );
}
