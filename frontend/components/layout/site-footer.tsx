export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-paper py-5">
      <div className="site-shell flex flex-wrap items-center justify-center gap-3 text-xs text-muted-ink sm:text-sm">
        <span>宋世华</span>
        <span aria-hidden="true">·</span>
        <span>Beijing Jiaotong University</span>
        <span aria-hidden="true" className="mx-3 hidden h-4 w-px bg-line sm:block" />
        <a className="font-medium hover:text-brand" href="https://github.com/songshihua/" rel="noreferrer" target="_blank">
          github.com/songshihua
        </a>
      </div>
    </footer>
  );
}
