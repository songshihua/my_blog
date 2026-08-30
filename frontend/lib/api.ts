import {
  demoArticles,
  demoNoteTree,
  demoProjects,
  demoRadarSources,
  type Article,
  type NoteCategory,
  type NoteTree,
  type Project,
  type RadarItem,
  type RadarSource,
  type RadarStats,
} from './site-data';

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
).replace(/\/$/, '');

type Paginated<T> = {
  results: T[];
  next?: string | null;
};

export type RadarSyncResult = {
  source_type: string;
  name: string;
  status: 'success' | 'failed' | 'skipped';
  inserted: number;
  updated: number;
  skipped: number;
  message: string;
};

export type RadarSyncResponse = {
  status: 'success' | 'partial' | 'error';
  message: string;
  inserted: number;
  updated: number;
  skipped: number;
  results: RadarSyncResult[];
};

export type RadarBrief = {
  title: string;
  overview: string;
  highlights: Array<{
    item_id: number;
    title: string;
    url: string;
    insight: string;
  }>;
  trends: string[];
  watchlist: string[];
  source_count: number;
  period_start: string;
  period_end: string;
  generated_at: string;
  model: string;
  cached: boolean;
};

export class RadarSyncRequestError extends Error {
  retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message);
    this.name = 'RadarSyncRequestError';
    this.retryAfter = retryAfter;
  }
}

export class RadarBriefRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RadarBriefRequestError';
  }
}

async function fetchWithFallback<T>(path: string, fallback: T): Promise<T> {
  try {
    const url = /^https?:\/\//i.test(path) ? path : `${API_BASE}${path}`;
    const response = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(1800),
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    // The frontend remains reviewable before MySQL/Django is started. Once the API
    // responds, the same components render database-backed content automatically.
    return fallback;
  }
}

export async function getProjects(): Promise<Project[]> {
  const data = await fetchWithFallback<Paginated<Project>>(
    '/projects/?page_size=50',
    { results: demoProjects },
  );
  return data.results;
}

export async function getArticles(): Promise<Article[]> {
  const data = await fetchWithFallback<Paginated<Article>>('/articles/', {
    results: demoArticles,
  });
  return data.results;
}

export async function getArticle(slug: string): Promise<Article | null> {
  const fallback =
    demoArticles.find((article) => article.slug === slug) ?? null;
  return fetchWithFallback<Article | null>(
    `/articles/${encodeURIComponent(slug)}/`,
    fallback,
  );
}

export async function getNoteTree(): Promise<NoteTree> {
  return fetchWithFallback<NoteTree>('/articles/tree/', demoNoteTree);
}

export function getBackendFileUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  try {
    const apiUrl = new URL(API_BASE);
    return new URL(path, apiUrl.origin).toString();
  } catch {
    return path;
  }
}

export class NoteImportRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoteImportRequestError';
  }
}

export class NoteCategoryRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoteCategoryRequestError';
  }
}

export class NoteManagementRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoteManagementRequestError';
  }
}

function firstApiError(payload: Record<string, unknown>): string | null {
  if (typeof payload.detail === 'string') return payload.detail;
  const value = Object.values(payload)
    .flat(Infinity)
    .find((item) => typeof item === 'string');
  return typeof value === 'string' ? value : null;
}

export async function createNoteCategory(input: {
  name: string;
  parentSlug: string | null;
}): Promise<NoteCategory> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/articles/categories/`, {
      method: 'POST',
      body: JSON.stringify({
        name: input.name.trim(),
        parent_slug: input.parentSlug,
      }),
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === 'TimeoutError'
        ? '新建目录超时，请稍后重试。'
        : '无法连接后端目录服务，请确认 Django 已启动。';
    throw new NoteCategoryRequestError(message);
  }

  const payload = (await response.json().catch(() => ({}))) as Record<
    string,
    unknown
  >;
  if (!response.ok) {
    throw new NoteCategoryRequestError(
      firstApiError(payload) ?? `新建目录失败（HTTP ${response.status}）。`,
    );
  }
  if (typeof payload.slug !== 'string' || typeof payload.name !== 'string') {
    throw new NoteCategoryRequestError('后端返回了无法识别的目录数据。');
  }
  return payload as NoteCategory;
}

async function deleteNoteResource(path: string, fallbackMessage: string) {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === 'TimeoutError'
        ? '删除请求超时，请稍后重试。'
        : '无法连接后端笔记管理服务，请确认 Django 已启动。';
    throw new NoteManagementRequestError(message);
  }

  if (response.ok) return;
  const payload = (await response.json().catch(() => ({}))) as Record<
    string,
    unknown
  >;
  throw new NoteManagementRequestError(
    firstApiError(payload) ?? `${fallbackMessage}（HTTP ${response.status}）。`,
  );
}

export async function deleteNoteArticle(slug: string): Promise<void> {
  await deleteNoteResource(
    `/articles/${encodeURIComponent(slug)}/manage/`,
    '删除文章失败',
  );
}

export async function deleteNoteCategory(slug: string): Promise<void> {
  await deleteNoteResource(
    `/articles/categories/${encodeURIComponent(slug)}/`,
    '删除目录失败',
  );
}

export async function uploadNoteFile(input: {
  file: File;
  categorySlug: string;
  title?: string;
  summary?: string;
}): Promise<Article> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('category_slug', input.categorySlug);
  if (input.title?.trim()) form.append('title', input.title.trim());
  if (input.summary?.trim()) form.append('summary', input.summary.trim());

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/articles/import/`, {
      method: 'POST',
      body: form,
      cache: 'no-store',
      signal: AbortSignal.timeout(120_000),
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === 'TimeoutError'
        ? '文件解析超时，请检查文件大小后重试。'
        : '无法连接后端导入服务，请确认 Django 已启动。';
    throw new NoteImportRequestError(message);
  }

  const payload = (await response.json().catch(() => ({}))) as Record<
    string,
    unknown
  >;
  if (!response.ok) {
    const detail = firstApiError(payload);
    throw new NoteImportRequestError(
      detail ?? `导入失败（HTTP ${response.status}）。`,
    );
  }
  if (typeof payload.slug !== 'string') {
    throw new NoteImportRequestError('后端返回了无法识别的笔记数据。');
  }
  return payload as Article;
}

export async function getRadarItems(): Promise<RadarItem[]> {
  let page = await fetchWithFallback<Paginated<RadarItem>>(
    '/radar/items/?page_size=50',
    { results: [], next: null },
  );
  const items = [...page.results];
  const visitedPages = new Set<string>();

  while (page.next && !visitedPages.has(page.next)) {
    visitedPages.add(page.next);
    page = await fetchWithFallback<Paginated<RadarItem>>(page.next, {
      results: [],
      next: null,
    });
    items.push(...page.results);
  }

  return items.filter((item) => !item.is_demo);
}

export async function getRadarSources(): Promise<RadarSource[]> {
  return fetchWithFallback<RadarSource[]>('/radar/sources/', demoRadarSources);
}

export async function getRadarStats(): Promise<RadarStats> {
  return fetchWithFallback<RadarStats>('/radar/stats/', {
    today_count: 0,
    week_count: 0,
    total_count: 0,
    by_kind: {},
    last_success_at: null,
    contains_demo_data: false,
  });
}

export async function syncRadarSources(): Promise<RadarSyncResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/radar/sync/`, {
      method: 'POST',
      cache: 'no-store',
      signal: AbortSignal.timeout(180_000),
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === 'TimeoutError'
        ? '同步超时，请稍后重试。'
        : '无法连接后端同步服务，请确认 Django 已启动。';
    throw new RadarSyncRequestError(message);
  }

  const payload = (await response.json().catch(() => ({}))) as {
    detail?: string;
    retry_after?: number;
  } & Partial<RadarSyncResponse>;
  if (!response.ok) {
    throw new RadarSyncRequestError(
      payload.detail || `同步请求失败（HTTP ${response.status}）。`,
      payload.retry_after,
    );
  }
  if (!payload.status || !payload.message || !Array.isArray(payload.results)) {
    throw new RadarSyncRequestError('后端返回了无法识别的同步结果。');
  }
  return payload as RadarSyncResponse;
}

export async function generateRadarBrief(): Promise<RadarBrief> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/radar/brief/`, {
      method: 'POST',
      cache: 'no-store',
      signal: AbortSignal.timeout(120_000),
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === 'TimeoutError'
        ? '简报生成超时，请稍后重试。'
        : '无法连接简报生成服务，请确认 Django 已启动。';
    throw new RadarBriefRequestError(message);
  }

  const payload = (await response.json().catch(() => ({}))) as {
    detail?: string;
  } & Partial<RadarBrief>;
  if (!response.ok) {
    throw new RadarBriefRequestError(
      payload.detail || `简报生成失败（HTTP ${response.status}）。`,
    );
  }
  if (
    !payload.title ||
    typeof payload.overview !== 'string' ||
    !Array.isArray(payload.highlights) ||
    !Array.isArray(payload.trends) ||
    !Array.isArray(payload.watchlist)
  ) {
    throw new RadarBriefRequestError('后端返回了无法识别的简报。');
  }
  return payload as RadarBrief;
}
