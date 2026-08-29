export type Topic = { name: string; slug: string; color?: string };

export type Project = {
  title: string;
  slug: string;
  subtitle: string;
  category: string;
  category_label: string;
  summary: string;
  problem?: string;
  approach?: string;
  outcome?: string;
  topics: Topic[];
  repository_url: string;
  is_demo: boolean;
};

export type Article = {
  title: string;
  slug: string;
  summary: string;
  category: { name: string; slug: string };
  topics: Topic[];
  published_at: string;
  updated_at: string;
  reading_minutes: number;
  repository_url?: string;
  is_demo: boolean;
};

export type RadarItem = {
  id: number;
  title: string;
  original_url: string;
  summary: string;
  source: { name: string; source_type: string; status?: string };
  kind: string;
  kind_label: string;
  topics: Topic[];
  authors: string[];
  published_at: string;
  is_featured: boolean;
  is_demo: boolean;
  ai_summary?: Record<string, string>;
};

export const topics: Topic[] = [
  { name: 'Speculative Decoding', slug: 'speculative-decoding', color: '#315CFF' },
  { name: 'KV Cache', slug: 'kv-cache', color: '#745CFA' },
  { name: 'LLM Serving', slug: 'llm-serving', color: '#168847' },
  { name: 'Continuous Batching', slug: 'continuous-batching', color: '#ED8612' },
  { name: 'Quantization', slug: 'quantization', color: '#A8329B' },
];

export const demoProjects: Project[] = [
  {
    title: 'SpecDecode Lab',
    slug: 'spec-decode-lab-sample',
    subtitle: '投机解码实验工作台',
    category: 'inference',
    category_label: '推理优化',
    summary: '用于理解候选生成、目标验证与接受/拒绝流程的概念工作台。',
    problem: '如何在保证输出质量的前提下理解投机解码的关键环节？',
    approach: '以可交互流程图拆解 Draft、Verify 与 Accept / Reject。',
    outcome: '当前图表与指标仅供界面演示，不代表真实实验结论。',
    topics: [topics[0], topics[2]],
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
  {
    title: 'KV Cache Observatory',
    slug: 'kv-cache-observatory-sample',
    subtitle: 'KV Cache 显存与吞吐分析面板',
    category: 'system',
    category_label: '系统实践',
    summary: '观察 KV Cache 分配、命中率与序列长度关系的概念面板。',
    problem: 'KV Cache 如何随上下文长度与并发变化？',
    approach: '用矩阵和时间线呈现缓存占用、复用与回收状态。',
    outcome: '等待接入真实实验数据。',
    topics: [topics[1]],
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
  {
    title: 'LLM Serving Notes',
    slug: 'llm-serving-notes-sample',
    subtitle: '推理优化知识图谱',
    category: 'learning',
    category_label: '学习实验',
    summary: '整理调度、批处理、系统资源与模型优化之间的关系。',
    problem: '推理系统的关键优化模块如何协同？',
    approach: '建立可持续更新的概念图与工程笔记。',
    outcome: '目前为学习型概念项目。',
    topics: [topics[2], topics[3]],
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
];

export const demoArticles: Article[] = [
  {
    title: '投机解码中的接受率、延迟与吞吐',
    slug: 'speculative-decoding-acceptance-sample',
    summary: '从核心直觉到系统指标，理解投机解码为何能够加速生成。',
    category: { name: '学习笔记', slug: 'learning-notes' },
    topics: [topics[0], topics[2]],
    published_at: '2026-08-29T08:30:00+08:00',
    updated_at: '2026-08-29T08:30:00+08:00',
    reading_minutes: 8,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
  {
    title: 'KV Cache 的显存瓶颈与优化思路',
    slug: 'kv-cache-memory-sample',
    summary: '梳理长上下文推理中的缓存占用、复用与调度问题。',
    category: { name: '学习笔记', slug: 'learning-notes' },
    topics: [topics[1]],
    published_at: '2026-08-26T08:30:00+08:00',
    updated_at: '2026-08-26T08:30:00+08:00',
    reading_minutes: 7,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
  {
    title: 'Continuous Batching 调度笔记',
    slug: 'continuous-batching-sample',
    summary: '记录动态批处理的吞吐、排队与公平性权衡。',
    category: { name: '学习笔记', slug: 'learning-notes' },
    topics: [topics[3]],
    published_at: '2026-08-23T08:30:00+08:00',
    updated_at: '2026-08-23T08:30:00+08:00',
    reading_minutes: 6,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
  },
];

export const demoRadarItems: RadarItem[] = [
  {
    id: 1,
    title: 'Fast Speculative Decoding for Production LLM Serving',
    original_url: 'https://arxiv.org/',
    summary: '提出面向生产环境的投机解码框架；本条仅用于呈现界面结构。',
    source: { name: 'arXiv', source_type: 'arxiv', status: 'disabled' },
    kind: 'paper',
    kind_label: '论文',
    topics: [topics[0], topics[2]],
    authors: ['Sample Author', 'Example Contributor'],
    published_at: '2026-08-29T08:20:00+08:00',
    is_featured: true,
    is_demo: true,
    ai_summary: {
      核心贡献: '界面示例：展示结构化摘要区域与研究关联。',
      实验结论: '示意数据：尚未连接真实论文来源，不构成实验结论。',
      与我的研究方向: '关联投机解码与高性能 LLM Serving。',
    },
  },
  {
    id: 2,
    title: 'Memory-Efficient KV Cache for Long-Context Inference',
    original_url: 'https://huggingface.co/',
    summary: '长上下文 KV Cache 管理界面示例，内容等待真实来源同步。',
    source: { name: 'Hugging Face', source_type: 'huggingface', status: 'disabled' },
    kind: 'model',
    kind_label: '模型',
    topics: [topics[1]],
    authors: ['Sample Team'],
    published_at: '2026-08-29T05:15:00+08:00',
    is_featured: false,
    is_demo: true,
  },
  {
    id: 3,
    title: 'Continuous Batching Under Dynamic Workloads',
    original_url: 'https://github.com/',
    summary: '动态请求负载的批处理调度演示条目。',
    source: { name: 'GitHub Trending', source_type: 'github', status: 'disabled' },
    kind: 'repository',
    kind_label: '开源项目',
    topics: [topics[3]],
    authors: ['Sample Maintainers'],
    published_at: '2026-08-29T02:10:00+08:00',
    is_featured: false,
    is_demo: true,
  },
];
