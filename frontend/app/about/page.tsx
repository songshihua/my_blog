import type { Metadata } from 'next';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteIcon } from '@/components/ui/site-icon';

export const metadata: Metadata = {
  title: '关于我',
  description: '宋世华的研究方向、技术兴趣与联系方式。',
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <SiteHeader activePath="/about" action="contact" />
      <div className="site-shell py-12 lg:py-20">
        <section className="grid gap-10 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="about-monogram" aria-hidden="true"><span>SS</span><b>INFERENCE<br />SYSTEMS</b></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand">About Me</p>
            <h1 className="mt-3 text-[clamp(2.6rem,5vw,5rem)] font-black leading-[1.05] tracking-[-0.055em]">把研究问题变成<br />可验证的工程系统。</h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-muted-ink">我是宋世华，北京交通大学硕士研究生。当前关注大模型推理优化，尤其是投机解码、KV Cache 管理和高性能 LLM Serving。这个站点用于长期记录问题定义、复现实验、系统分析与学习复盘。</p>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {[['研究方向', '大模型推理优化'], ['所在学校', '北京交通大学'], ['当前状态', '本地开发中']].map(([label, value]) => <div className="about-fact" key={label}><span>{label}</span><strong>{value}</strong></div>)}
            </div>
            <div className="mt-8 flex flex-wrap gap-3"><a className="primary-action" href="https://github.com/songshihua/" rel="noreferrer" target="_blank"><SiteIcon name="github" /> GitHub</a><a className="secondary-action" href="mailto:songshihua@example.com">联系我 <SiteIcon name="arrow" /></a></div>
            <p className="mt-5 text-xs text-muted-ink">联系邮箱当前为配置占位符，请在 Django Admin 或环境配置中替换后再公开。</p>
          </div>
        </section>
      </div>
      <SiteFooter />
    </main>
  );
}
