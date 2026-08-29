import type { Metadata } from 'next';
import Link from 'next/link';

import { SiteHeader } from '@/components/layout/site-header';
import { ArticleActions, CodeBlock, ReadingProgress } from '@/components/notes/article-tools';
import { SiteIcon } from '@/components/ui/site-icon';
import { PerformanceChart, SpeculativePipeline } from '@/components/visuals/research-diagrams';
import { getArticles } from '@/lib/api';

type PageProps = { params: Promise<{ slug: string }> };

async function resolveArticle(slug: string) {
  const articles = await getArticles();
  return articles.find((article) => article.slug === slug) ?? articles[0];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await resolveArticle(slug);
  return {
    title: article?.title ?? '技术笔记',
    description: article?.summary,
    openGraph: { title: article?.title, description: article?.summary, images: [] },
    twitter: { card: 'summary', title: article?.title, description: article?.summary, images: [] },
  };
}

export default async function NoteDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const article = await resolveArticle(slug);
  if (!article) return null;

  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/notes" />
      <div className="article-layout">
        <aside className="article-toc">
          <div className="sticky top-24">
            <h2>本文目录</h2>
            <nav aria-label="文章目录">
              {[['问题背景', 'background'], ['核心直觉', 'intuition'], ['接受率与收益', 'metrics'], ['实验设计', 'experiment'], ['进一步阅读', 'more']].map(([label, id], index) => <a className={index === 1 ? 'active' : ''} href={`#${id}`} key={id}>{label}</a>)}
            </nav>
            <ReadingProgress />
          </div>
        </aside>

        <article className="article-body">
          <header className="border-b border-line pb-4">
            <div className="flex flex-wrap items-center gap-3"><span className="demo-badge">示例文章 / SAMPLE</span><span className="text-xs font-bold text-violet-700">LLM INFERENCE</span></div>
            <h1 className="mt-3 text-[clamp(2rem,3.6vw,3.1rem)] font-black leading-tight tracking-[-0.035em]">{article.title}</h1>
            <p className="mt-2 text-sm text-muted-ink">{article.summary}</p>
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-ink"><span>宋世华 · 北京交通大学硕士</span><span>{article.category.name} · 约 {article.reading_minutes} 分钟阅读</span><span>内容示意</span></div>
          </header>

          <section id="background">
            <h2>问题背景</h2>
            <p>在自回归生成中，目标模型每次通常只输出一个 token，顺序依赖会带来大量串行等待。投机解码通过小模型一次提出多个候选，再由目标模型并行验证，在保持输出分布一致的同时争取更高吞吐。</p>
            <div className="conclusion-callout"><span aria-hidden="true">◇</span><div><strong>核心结论</strong><p>以下内容与数据仅用于界面展示；真实结论需要由可复现实验、硬件配置和完整基线共同支撑。</p></div></div>
          </section>

          <section id="intuition">
            <h2>核心直觉</h2>
            <p>Draft 模型快速提出 k 个候选；Target 模型进行校验。最长匹配前缀被接受，其余位置回到目标模型重采样。</p>
            <div className="article-figure"><SpeculativePipeline /><p>图 1 · 投机解码流程（概念示意）</p></div>
          </section>

          <section className="grid gap-3 xl:grid-cols-2" id="metrics">
            <CodeBlock />
            <div className="article-figure"><div className="px-3 pt-2 text-xs font-bold">吞吐—延迟关系（示意数据）</div><PerformanceChart /><p>图 2 · 曲线不代表真实实验结果</p></div>
          </section>

          <section id="experiment">
            <h2>实验设计</h2>
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="article-table"><thead><tr><th>变量</th><th>影响</th><th>观察方式</th></tr></thead><tbody><tr><td>接受率</td><td>通常与更高吞吐、更低延迟相关</td><td>由 Draft/Target 质量与温度共同决定</td></tr><tr><td>提案长度 k</td><td>增加并行机会，也会增加验证成本</td><td>比较不同 k 下的端到端曲线</td></tr><tr><td>模型与硬件</td><td>决定可达到的性能上界</td><td>固定环境并完整记录配置</td></tr></tbody></table>
            </div>
            <blockquote>投机解码的价值不是一条孤立的加速数字，而是计算、验证、调度与真实负载之间的系统性权衡。</blockquote>
          </section>

          <section id="more">
            <h2>进一步阅读</h2>
            <p>下一步将补充真实论文引用、复现实验配置和可下载数据。正式内容发布前，演示标识不会移除。</p>
            <nav className="article-pager"><Link href="/notes/kv-cache-memory-sample">← 上一篇<span>KV Cache 的显存瓶颈与优化思路</span></Link><Link className="text-right" href="/notes/continuous-batching-sample">下一篇 →<span>Continuous Batching 调度笔记</span></Link></nav>
          </section>
        </article>

        <aside className="article-aside">
          <div className="sticky top-24 space-y-4">
            <section className="side-card"><h2>文章信息</h2><div className="mt-4 space-y-4 text-xs"><div><span className="text-muted-ink">最后更新</span><p className="mt-1 font-medium">{article.updated_at.slice(0, 10)}</p></div><div><span className="text-muted-ink">标签</span><div className="mt-2 flex flex-wrap gap-2">{article.topics.map((topic) => <span className="tag-chip" key={topic.slug}>{topic.name}</span>)}</div></div></div><a className="primary-action mt-4 w-full" href={article.repository_url} rel="noreferrer" target="_blank"><SiteIcon name="github" /> 在 GitHub 查看</a></section>
            <section className="side-card"><h2>相关文章</h2><Link className="related-link" href="/notes/kv-cache-memory-sample"><SiteIcon name="document" />KV Cache 的显存瓶颈与优化思路<SiteIcon name="arrow" /></Link><Link className="related-link" href="/notes/continuous-batching-sample"><SiteIcon name="document" />Continuous Batching 调度笔记<SiteIcon name="arrow" /></Link></section>
            <ArticleActions />
          </div>
        </aside>
      </div>
    </main>
  );
}
