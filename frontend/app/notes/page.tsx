import type { Metadata } from 'next';
import Link from 'next/link';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteIcon } from '@/components/ui/site-icon';
import { getArticles } from '@/lib/api';

export const metadata: Metadata = {
  title: '技术笔记',
  description: '大模型推理优化、投机解码、KV Cache 与服务系统学习笔记。',
};

export default async function NotesPage() {
  const articles = await getArticles();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="site-shell py-10">
        <header className="max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand">Research Notes</p>
          <h1 className="mt-2 text-[clamp(2.2rem,4vw,3.8rem)] font-black tracking-tight">技术笔记与学习记录</h1>
          <p className="mt-3 leading-7 text-muted-ink">把论文理解、实验设计和工程复盘沉淀成可以检索、复用和持续修订的研究资料。</p>
        </header>
        <div className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_310px]">
          <section className="space-y-3" aria-label="文章列表">
            {articles.map((article, index) => (
              <Link className="note-card" href={`/notes/${article.slug}`} key={article.slug}>
                <div className="flex items-center gap-2 text-xs text-muted-ink"><span className="demo-badge">SAMPLE</span><time dateTime={article.published_at}>{article.published_at.slice(0, 10)}</time><span>·</span><span>约 {article.reading_minutes} 分钟</span></div>
                <h2 className="mt-3 text-xl font-black tracking-tight">{article.title}</h2>
                <p className="mt-2 text-sm leading-7 text-muted-ink">{article.summary}</p>
                <div className="mt-4 flex items-center gap-2">{article.topics.map((topic) => <span className="tag-chip" key={topic.slug}>{topic.name}</span>)}<SiteIcon className="ml-auto size-5 text-brand" name="arrow" /></div>
                <span className="absolute right-5 top-4 text-5xl font-black text-brand-soft/55">0{index + 1}</span>
              </Link>
            ))}
          </section>
          <aside className="space-y-3">
            <section className="side-card"><h2>笔记主题</h2>{['投机解码', 'KV Cache', 'LLM Serving', '系统设计'].map((item) => <div className="overview-row" key={item}><span className="size-2 rounded-full bg-brand" /><span className="flex-1">{item}</span><span>›</span></div>)}</section>
            <section className="side-card"><h2>内容说明</h2><p className="text-xs leading-6 text-muted-ink">当前文章用于验证本地开发、API 和排版。所有示意曲线、指标与论文条目均明确标记，不作为真实研究成果。</p></section>
          </aside>
        </div>
      </div>
      <SiteFooter />
    </main>
  );
}
