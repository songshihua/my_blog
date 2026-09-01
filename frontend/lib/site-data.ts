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
  demo_url?: string;
  is_featured?: boolean;
  is_demo: boolean;
  external_source?: 'manual' | 'github';
  source_metadata?: {
    language?: string;
    stars?: number;
    forks?: number;
    license?: string;
    full_name?: string;
    topics?: string[];
    open_issues?: number;
    default_branch?: string;
    homepage?: string;
    archived?: boolean;
    fork?: boolean;
  };
  last_synced_at?: string | null;
  updated_at?: string;
};

export type NoteCategory = {
  name: string;
  slug: string;
  description: string;
  sort_order: number;
  parent_slug: string | null;
  ancestors: Array<{ name: string; slug: string }>;
};

export type ArticleOutlineItem = {
  id: string;
  text: string;
  level: number;
};

export type ArticleSourceFile = {
  original_filename: string;
  source_format: 'markdown' | 'docx' | 'pdf';
  source_format_label: string;
  size_bytes: number;
  download_url: string;
  preview_url: string | null;
};

export type Article = {
  title: string;
  slug: string;
  summary: string;
  category: NoteCategory;
  topics: Topic[];
  published_at: string | null;
  updated_at: string;
  reading_minutes: number;
  repository_url?: string;
  is_demo: boolean;
  is_featured?: boolean;
  body_markdown?: string;
  outline?: ArticleOutlineItem[];
  source_file?: ArticleSourceFile | null;
};

export type NoteTree = {
  categories: NoteCategory[];
  articles: Article[];
  import_enabled: boolean;
  authoring_enabled: boolean;
  max_category_depth: number;
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
  repository_metrics?: {
    stars: number;
    forks: number;
    language: string;
  } | null;
};

export type RadarSource = {
  name: string;
  source_type: string;
  source_type_label: string;
  homepage_url: string;
  is_enabled: boolean;
  status: 'disabled' | 'idle' | 'running' | 'success' | 'error';
  status_label: string;
  is_configured: boolean;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  last_item_count: number;
};

export type RadarStats = {
  today_count: number;
  week_count: number;
  total_count: number;
  by_kind: Record<string, number>;
  last_success_at: string | null;
  contains_demo_data: boolean;
};

export const topics: Topic[] = [
  {
    name: 'Speculative Decoding',
    slug: 'speculative-decoding',
    color: '#315CFF',
  },
  { name: 'KV Cache', slug: 'kv-cache', color: '#745CFA' },
  { name: 'LLM Serving', slug: 'llm-serving', color: '#168847' },
  {
    name: 'Continuous Batching',
    slug: 'continuous-batching',
    color: '#ED8612',
  },
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
    external_source: 'manual',
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
    external_source: 'manual',
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
    external_source: 'manual',
  },
];

export const demoArticles: Article[] = [
  {
    title: '投机解码中的接受率、延迟与吞吐',
    slug: 'speculative-decoding-acceptance-sample',
    summary: '从核心直觉到系统指标，理解投机解码为何能够加速生成。',
    category: {
      name: '学习笔记',
      slug: 'notes',
      description: '',
      sort_order: 10,
      parent_slug: 'inference-optimization',
      ancestors: [
        { name: 'AI 技术', slug: 'ai-technology' },
        { name: '大模型', slug: 'large-models' },
        { name: '推理优化', slug: 'inference-optimization' },
      ],
    },
    topics: [topics[0], topics[2]],
    published_at: '2026-08-29T08:30:00+08:00',
    updated_at: '2026-08-29T08:30:00+08:00',
    reading_minutes: 8,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
    body_markdown:
      '# 投机解码中的接受率、延迟与吞吐\n\n## 问题背景\n\n从核心直觉到系统指标，理解投机解码为何能够加速生成。\n\n## 核心直觉\n\nDraft 模型生成候选，Target 模型并行验证并接受最长匹配前缀。',
    outline: [
      {
        id: '投机解码中的接受率-延迟与吞吐',
        text: '投机解码中的接受率、延迟与吞吐',
        level: 1,
      },
      { id: '问题背景', text: '问题背景', level: 2 },
      { id: '核心直觉', text: '核心直觉', level: 2 },
    ],
  },
  {
    title: 'KV Cache 的显存瓶颈与优化思路',
    slug: 'kv-cache-memory-sample',
    summary: '梳理长上下文推理中的缓存占用、复用与调度问题。',
    category: {
      name: '学习笔记',
      slug: 'notes',
      description: '',
      sort_order: 10,
      parent_slug: 'inference-optimization',
      ancestors: [
        { name: 'AI 技术', slug: 'ai-technology' },
        { name: '大模型', slug: 'large-models' },
        { name: '推理优化', slug: 'inference-optimization' },
      ],
    },
    topics: [topics[1]],
    published_at: '2026-08-26T08:30:00+08:00',
    updated_at: '2026-08-26T08:30:00+08:00',
    reading_minutes: 7,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
    body_markdown:
      '# KV Cache 的显存瓶颈与优化思路\n\n## 缓存占用\n\n梳理长上下文推理中的缓存占用、复用与调度问题。',
    outline: [
      {
        id: 'kv-cache-的显存瓶颈与优化思路',
        text: 'KV Cache 的显存瓶颈与优化思路',
        level: 1,
      },
      { id: '缓存占用', text: '缓存占用', level: 2 },
    ],
  },
  {
    title: 'Continuous Batching 调度笔记',
    slug: 'continuous-batching-sample',
    summary: '记录动态批处理的吞吐、排队与公平性权衡。',
    category: {
      name: '学习笔记',
      slug: 'notes',
      description: '',
      sort_order: 10,
      parent_slug: 'inference-optimization',
      ancestors: [
        { name: 'AI 技术', slug: 'ai-technology' },
        { name: '大模型', slug: 'large-models' },
        { name: '推理优化', slug: 'inference-optimization' },
      ],
    },
    topics: [topics[3]],
    published_at: '2026-08-23T08:30:00+08:00',
    updated_at: '2026-08-23T08:30:00+08:00',
    reading_minutes: 6,
    repository_url: 'https://github.com/songshihua/',
    is_demo: true,
    body_markdown:
      '# Continuous Batching 调度笔记\n\n## 调度目标\n\n记录动态批处理的吞吐、排队与公平性权衡。',
    outline: [
      {
        id: 'continuous-batching-调度笔记',
        text: 'Continuous Batching 调度笔记',
        level: 1,
      },
      { id: '调度目标', text: '调度目标', level: 2 },
    ],
  },
];

export const demoNoteTree: NoteTree = {
  categories: [
    {
      name: 'AI 技术',
      slug: 'ai-technology',
      description: '',
      sort_order: 10,
      parent_slug: null,
      ancestors: [],
    },
    {
      name: '大模型',
      slug: 'large-models',
      description: '',
      sort_order: 10,
      parent_slug: 'ai-technology',
      ancestors: [{ name: 'AI 技术', slug: 'ai-technology' }],
    },
    {
      name: '推理优化',
      slug: 'inference-optimization',
      description: '',
      sort_order: 10,
      parent_slug: 'large-models',
      ancestors: [
        { name: 'AI 技术', slug: 'ai-technology' },
        { name: '大模型', slug: 'large-models' },
      ],
    },
    {
      name: '学习笔记',
      slug: 'notes',
      description: '',
      sort_order: 10,
      parent_slug: 'inference-optimization',
      ancestors: [
        { name: 'AI 技术', slug: 'ai-technology' },
        { name: '大模型', slug: 'large-models' },
        { name: '推理优化', slug: 'inference-optimization' },
      ],
    },
  ],
  articles: demoArticles,
  import_enabled: false,
  authoring_enabled: false,
  max_category_depth: 8,
};

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
    source: {
      name: 'Hugging Face',
      source_type: 'huggingface',
      status: 'disabled',
    },
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
    source: {
      name: 'GitHub 热门项目',
      source_type: 'github',
      status: 'disabled',
    },
    kind: 'repository',
    kind_label: '开源项目',
    topics: [topics[3]],
    authors: ['Sample Maintainers'],
    published_at: '2026-08-29T02:10:00+08:00',
    is_featured: false,
    is_demo: true,
  },
];

export const demoRadarSources: RadarSource[] = [
  ['arxiv', 'arXiv API', 'https://arxiv.org/'],
  [
    'github',
    'GitHub 热门项目',
    'https://github.com/search?q=llm&type=repositories',
  ],
  ['huggingface', 'Hugging Face Hub', 'https://huggingface.co/'],
].map(([source_type, name, homepage_url]) => ({
  source_type,
  source_type_label: name,
  name,
  homepage_url,
  is_enabled: false,
  status: 'disabled',
  status_label: '未启用',
  is_configured: false,
  last_attempt_at: null,
  last_success_at: null,
  last_error_at: null,
  last_item_count: 0,
}));

export const demoRadarStats: RadarStats = {
  today_count: demoRadarItems.length,
  week_count: demoRadarItems.length,
  total_count: demoRadarItems.length,
  by_kind: { paper: 1, repository: 1, model: 1 },
  last_success_at: null,
  contains_demo_data: true,
};
