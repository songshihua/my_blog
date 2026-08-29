import { demoArticles, demoProjects, demoRadarItems, type Article, type Project, type RadarItem } from './site-data';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

type Paginated<T> = { results: T[] };

async function fetchWithFallback<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
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
  const data = await fetchWithFallback<Paginated<Project>>('/projects/', { results: demoProjects });
  return data.results;
}

export async function getArticles(): Promise<Article[]> {
  const data = await fetchWithFallback<Paginated<Article>>('/articles/', { results: demoArticles });
  return data.results;
}

export async function getRadarItems(): Promise<RadarItem[]> {
  const data = await fetchWithFallback<Paginated<RadarItem>>('/radar/items/', { results: demoRadarItems });
  return data.results;
}
