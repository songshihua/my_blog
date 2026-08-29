import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: {
    default: 'SS·LAB｜宋世华的研究与技术博客',
    template: '%s｜SS·LAB',
  },
  description: '宋世华的个人研究主页，记录大模型推理优化、投机解码、KV Cache 与 LLM Serving 实践。',
  openGraph: {
    type: 'website',
    locale: 'zh_CN',
    title: 'SS·LAB｜宋世华的研究与技术博客',
    description: '大模型推理优化、投机解码、KV Cache 与 LLM Serving 研究实践。',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'SS·LAB 社交分享封面' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SS·LAB｜宋世华的研究与技术博客',
    description: '大模型推理优化、投机解码、KV Cache 与 LLM Serving 研究实践。',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
