import Link from 'next/link';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteIcon } from '@/components/ui/site-icon';
import {
  KvCacheMatrix,
  PerformanceChart,
  SpeculativePipeline,
} from '@/components/visuals/research-diagrams';
import { getArticles } from '@/lib/api';

const researchCards = [
  {
    title: '投机解码',
    description:
      '研究候选生成与目标验证机制，关注接受率、草稿长度与端到端延迟的关系。',
    visual: 'pipeline',
  },
  {
    title: 'KV Cache 优化',
    description: '探索缓存分配、复用与压缩策略，减少显存占用并稳定长序列推理。',
    visual: 'cache',
  },
  {
    title: '高性能推理服务',
    description:
      '构建高吞吐、低延迟、可扩展的服务工作流，优化调度、批处理与资源利用。',
    visual: 'serving',
  },
];

export default async function HomePage() {
  const articles = await getArticles();

  return (
    <main className="min-h-screen bg-grid-paper text-ink">
      <SiteHeader activePath="/" action="contact" />

      <div className="site-shell py-8 lg:py-10">
        <section className="grid items-center gap-9 lg:grid-cols-[0.84fr_1.16fr]">
          <div>
            <p className="mb-5 flex items-center gap-2 text-sm font-semibold text-brand">
              <span className="inline-flex size-3 rounded-full bg-brand ring-4 ring-brand-soft" />
              北京交通大学 · 硕士研究生
            </p>
            <h1 className="max-w-[700px] text-[clamp(2.5rem,4.4vw,4.15rem)] font-black leading-[1.13] tracking-[-0.055em]">
              你好，我是宋世华。
              <span className="mt-2 block">让大模型推理更快、更省、更稳。</span>
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-muted-ink">
              研究方向：大模型推理优化，关注投机解码、KV Cache 与高性能 LLM
              Serving。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link className="primary-action" href="/projects">
                查看研究 <SiteIcon name="arrow" />
              </Link>
              <Link className="secondary-action" href="/radar">
                进入 AI 前沿 <SiteIcon name="arrow" />
              </Link>
            </div>
            <a
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold hover:text-brand"
              href="https://github.com/songshihua/"
              rel="noreferrer"
              target="_blank"
            >
              <SiteIcon className="size-5" name="github" />{' '}
              github.com/songshihua
            </a>
          </div>

          <section className="lab-panel" aria-label="推理优化实验室概览">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight">
                Inference Lab
              </h2>
              <span className="flex items-center gap-2 text-sm font-medium text-success">
                <span className="size-2 rounded-full bg-success" /> Local
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-[1.08fr_1fr]">
              <pre className="code-window" aria-label="投机解码伪代码">
                <code>
                  <span>
                    <i>1</i>
                    <b># Inference optimization</b>
                  </span>
                  {'\n'}
                  <span>
                    <i>2</i>
                    <em>from</em> typing <em>import</em> Optional
                  </span>
                  {'\n\n'}
                  <span>
                    <i>4</i>
                    <em>def</em> <strong>speculative_decode</strong>(model,
                    draft):
                  </span>
                  {'\n'}
                  <span>
                    <i>5</i> draft_tokens = draft.generate()
                  </span>
                  {'\n'}
                  <span>
                    <i>6</i> verified = model.verify(draft_tokens)
                  </span>
                  {'\n'}
                  <span>
                    <i>7</i> <em>return</em> accept_or_reject(verified)
                  </span>
                </code>
              </pre>
              <div className="chart-window">
                <PerformanceChart dark />
              </div>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {['ϟ  Speculative Decoding', '◇  KV Cache', '≡  LLM Serving'].map(
                (label) => (
                  <div className="lab-chip" key={label}>
                    {label}
                  </div>
                ),
              )}
            </div>
          </section>
        </section>

        <section className="mt-4" aria-labelledby="research-heading">
          <h2 className="mb-2 px-3 text-sm font-bold" id="research-heading">
            研究方向
          </h2>
          <div className="grid gap-3 lg:grid-cols-3">
            {researchCards.map((card) => (
              <article className="research-card" key={card.title}>
                <div className="min-w-0 flex-1">
                  {card.visual === 'pipeline' && (
                    <SpeculativePipeline compact />
                  )}
                  {card.visual === 'cache' && <KvCacheMatrix />}
                  {card.visual === 'serving' && (
                    <svg
                      aria-label="推理服务流程"
                      className="h-36 w-full"
                      viewBox="0 0 390 150"
                    >
                      <defs>
                        <marker
                          id="home-arrow"
                          markerHeight="7"
                          markerWidth="7"
                          orient="auto"
                          refX="6"
                          refY="3"
                        >
                          <path d="M0 0 6 3 0 6" fill="none" stroke="#4f535d" />
                        </marker>
                      </defs>
                      <text fontSize="11" x="12" y="78">
                        Request
                      </text>
                      <path
                        d="M65 74h35"
                        markerEnd="url(#home-arrow)"
                        stroke="#4f535d"
                      />
                      {['Prefill', 'Decode', 'Batching', 'Scheduling'].map(
                        (label, i) => (
                          <g key={label}>
                            <rect
                              fill="#fff"
                              height="25"
                              rx="5"
                              stroke="#7895ff"
                              width="95"
                              x="112"
                              y={10 + i * 33}
                            />
                            <text
                              fill="#244dd8"
                              fontSize="10"
                              textAnchor="middle"
                              x="159"
                              y={26 + i * 33}
                            >
                              {label}
                            </text>
                          </g>
                        ),
                      )}
                      <path
                        d="M220 74h38"
                        markerEnd="url(#home-arrow)"
                        stroke="#4f535d"
                      />
                      <text
                        fontSize="11"
                        fontWeight="700"
                        textAnchor="middle"
                        x="320"
                        y="67"
                      >
                        GPU
                      </text>
                      <text
                        fontSize="11"
                        fontWeight="700"
                        textAnchor="middle"
                        x="320"
                        y="83"
                      >
                        Cluster
                      </text>
                    </svg>
                  )}
                </div>
                <div className="w-full border-t border-line pt-4 sm:w-[44%] sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0 lg:w-full lg:border-l-0 lg:border-t lg:pl-0 lg:pt-4 xl:w-[43%] xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0">
                  <h3 className="font-bold">{card.title}</h3>
                  <p className="mt-2 text-xs leading-6 text-muted-ink">
                    {card.description}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-3" aria-labelledby="recent-notes-heading">
          <h2 className="mb-1 px-3 text-sm font-bold" id="recent-notes-heading">
            近期笔记
          </h2>
          <div className="overflow-hidden rounded-xl border border-line bg-white/70">
            {articles.slice(0, 3).map((article) => (
              <Link
                className="note-row"
                href={`/notes/${article.slug}`}
                key={article.slug}
              >
                <SiteIcon className="size-5 text-brand" name="document" />
                <span className="font-semibold">{article.title}</span>
                <span className="tag-chip hidden sm:inline-flex">
                  {article.topics[0]?.name ?? article.category.name}
                </span>
                <time
                  className="text-xs text-muted-ink"
                  dateTime={article.published_at ?? undefined}
                >
                  {article.published_at?.slice(0, 10) ?? '未发布'}
                </time>
                <SiteIcon className="size-5 text-muted-ink" name="arrow" />
              </Link>
            ))}
          </div>
        </section>
      </div>

      <SiteFooter />
    </main>
  );
}
