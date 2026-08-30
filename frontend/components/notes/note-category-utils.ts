import type { NoteCategory } from '@/lib/site-data';

export function getNoteCategoryPath(category: NoteCategory): string {
  return [
    ...category.ancestors.map((ancestor) => ancestor.name),
    category.name,
  ].join(' / ');
}

export function orderNoteCategories(
  categories: NoteCategory[],
): NoteCategory[] {
  const bySlug = new Map(
    categories.map((category) => [category.slug, category] as const),
  );
  const children = new Map<string | null, NoteCategory[]>();

  for (const category of categories) {
    const parent =
      category.parent_slug && bySlug.has(category.parent_slug)
        ? category.parent_slug
        : null;
    const siblings = children.get(parent) ?? [];
    siblings.push(category);
    children.set(parent, siblings);
  }

  const sortSiblings = (items: NoteCategory[]) =>
    items.sort(
      (left, right) =>
        left.sort_order - right.sort_order ||
        left.name.localeCompare(right.name, 'zh-CN'),
    );
  children.forEach(sortSiblings);

  const ordered: NoteCategory[] = [];
  const visited = new Set<string>();
  const visit = (category: NoteCategory) => {
    if (visited.has(category.slug)) return;
    visited.add(category.slug);
    ordered.push(category);
    children.get(category.slug)?.forEach(visit);
  };

  children.get(null)?.forEach(visit);
  // Preserve malformed legacy/orphaned nodes rather than making them impossible
  // to select while the backend data is being repaired.
  sortSiblings([...categories]).forEach(visit);
  return ordered;
}
