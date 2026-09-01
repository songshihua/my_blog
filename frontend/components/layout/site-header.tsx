import Link from 'next/link';

const navItems = [
  { href: '/', label: '首页' },
  { href: '/notes', label: '笔记' },
  { href: '/radar', label: 'AI 前沿' },
  { href: '/about', label: '关于我' },
];

type SiteHeaderProps = {
  activePath: string;
  action?: 'contact' | 'github' | 'api';
};

export function SiteHeader({ activePath, action = 'github' }: SiteHeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/94 backdrop-blur-xl">
      <div className="site-shell grid h-16 grid-cols-[1fr_auto] items-center gap-4 md:grid-cols-[1fr_auto_1fr]">
        <Link className="justify-self-start text-[1.65rem] font-black tracking-[-0.055em]" href="/">
          SS·LAB
        </Link>

        <nav aria-label="主导航" className="hidden h-full items-center gap-1 md:flex">
          {navItems.map((item) => {
            const isActive =
              item.href === '/'
                ? activePath === '/'
                : activePath === item.href || activePath.startsWith(`${item.href}/`);
            return (
              <Link
                aria-current={isActive ? 'page' : undefined}
                className={`nav-link ${isActive ? 'nav-link-active' : ''}`}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden justify-self-end md:block">
          {action === 'contact' ? (
            <a className="header-action" href="mailto:songshihua@example.com">联系我</a>
          ) : action === 'api' ? (
            <a className="header-action" href="http://127.0.0.1:8000/api/docs/">API 文档</a>
          ) : (
            <a
              className="inline-flex items-center gap-2 text-sm font-semibold transition-colors hover:text-brand"
              href="https://github.com/songshihua/"
              rel="noreferrer"
              target="_blank"
            >
              <span aria-hidden="true" className="grid size-5 place-items-center rounded-full bg-ink text-[9px] text-white">GH</span>
              github.com/songshihua
            </a>
          )}
        </div>

        <details className="group relative justify-self-end md:hidden">
          <summary className="header-action cursor-pointer list-none">菜单</summary>
          <nav className="absolute right-0 top-12 w-48 rounded-xl border border-line bg-white p-2 shadow-xl" aria-label="移动端导航">
            {navItems.map((item) => (
              <Link className="block rounded-lg px-4 py-3 text-sm font-semibold hover:bg-brand-soft/50 hover:text-brand" href={item.href} key={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
        </details>
      </div>
    </header>
  );
}
