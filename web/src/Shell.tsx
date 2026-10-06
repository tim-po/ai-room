import {useEffect, useLayoutEffect, useState, type ReactNode} from 'react';
import {Outlet, ScrollRestoration, useLocation, useNavigate, useNavigation} from 'react-router';
import {bootstrap, type Notice} from './api';
import ErrorPage from './ErrorPage';
import {AppLink, isSpaPath} from './links';

export {AppLink, isSpaPath};

/** Plain <a> elements (lesson bodies, the skill map) also navigate inside the app when they can. */
function useLinkInterception() {
  const navigate = useNavigate();
  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!anchor || anchor.target || anchor.hasAttribute('download')) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin || !isSpaPath(url.pathname)) return;
      event.preventDefault();
      navigate(url.pathname + url.search + url.hash);
    }
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [navigate]);
}

function NavLink({to, active, children}: {to: string; active: boolean; children: ReactNode}) {
  return <AppLink to={to} aria-current={active ? 'page' : undefined}>{children}</AppLink>;
}

function ThemeToggle() {
  return (
    <button type="button" className="theme-toggle" data-theme-toggle aria-label="Сменить тему">
      <svg className="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" />
      </svg>
      <svg className="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden="true">
        <path d="M20 14.6A8.2 8.2 0 0 1 9.4 4a8.2 8.2 0 1 0 10.6 10.6Z" />
      </svg>
    </button>
  );
}

function Header() {
  const {pathname, search} = useLocation();
  const user = bootstrap.user;
  const onMap = pathname === '/' && (!!user || new URLSearchParams(search).get('view') === 'map');
  return (
    <header className="club-header">
      <AppLink className="brand" to="/">AI ROOM</AppLink>
      <nav aria-label="Главная навигация">
        <NavLink to="/?view=map" active={onMap}>Карта навыков</NavLink>
        <NavLink to="/catalogue" active={/^\/(catalogue|courses\/|lessons\/|materials\/)/.test(pathname)}>Библиотека</NavLink>
        <NavLink to="/profile" active={pathname === '/profile' || pathname === '/preferences'}>Моё обучение</NavLink>
        <NavLink to="/membership" active={pathname === '/membership'}>Клуб</NavLink>
        {user && user.role !== 'learner' && <a href="/admin">Мастерская</a>}
      </nav>
      <div className="header-account">
        <ThemeToggle />
        <AppLink to={user ? '/help' : '/login'} aria-current={pathname === '/help' ? 'page' : undefined}>{user ? 'Помощь' : 'Войти'}</AppLink>
        {user && (
          <form className="session-exit" method="post" action="/logout">
            <input type="hidden" name="csrf" value={bootstrap.csrf} />
            <button>Выйти</button>
          </form>
        )}
      </div>
    </header>
  );
}

export function Footer() {
  return <footer><div>AI Room Club · Независимая учебная среда<br />Контент и аккаунты этой версии — тестовые. Оплаты нет.</div></footer>;
}

/**
 * The first page shows what the server put in the bootstrap (an error status, flashed notices);
 * later pages show a notice passed in navigation state, e.g. navigate('/profile', {state: {notice}}).
 */
function usePageMessages() {
  const location = useLocation();
  const [first] = useState(location.key);
  const isFirst = location.key === first;
  const state = location.state as {notice?: string} | null;
  const notices: Notice[] = isFirst ? bootstrap.notices : state?.notice ? [{kind: 'success', text: state.notice}] : [];
  return {notices, error: isFirst ? bootstrap.error : null};
}

/**
 * html{scroll-behavior:smooth} is for in-page anchors. A new page should start at the top at once,
 * not slide up from the previous page's position: switch it off while ScrollRestoration (rendered
 * right after this, so its layout effect runs next) resets the scroll. Hash-only changes stay smooth.
 */
function InstantPageScroll() {
  const {pathname, search} = useLocation();
  useLayoutEffect(() => {
    const root = document.documentElement;
    root.style.scrollBehavior = 'auto';
    void getComputedStyle(root).scrollBehavior;   // apply now: scrollTo doesn't recalculate styles first
    const frame = requestAnimationFrame(() => { root.style.scrollBehavior = ''; });
    return () => { cancelAnimationFrame(frame); root.style.scrollBehavior = ''; };
  }, [pathname, search]);
  return null;
}

/** While the first page's data loads: the header and an empty sheet, so nothing jumps. */
export function ShellFallback() {
  return (
    <>
      <Header />
      <div className="shell"><main id="main" /></div>
    </>
  );
}

// React Router keys every full page load "default", so a fresh load (a link from a server page, a
// calendar reminder via /continue) would restore whatever scroll was last saved under that key.
// Fresh loads start at the top (or their #section); only a reload restores its position.
const loadType = (performance.getEntriesByType?.('navigation')[0] as PerformanceNavigationTiming | undefined)?.type;
const firstLoadKey = loadType === 'reload' ? `reload:${window.location.pathname}${window.location.search}` : `load:${Date.now()}`;
const scrollKey = (location: {key: string}) => (location.key === 'default' ? firstLoadKey : location.key);

/** --header-h: the sticky header's height, so sticky bars and anchors can sit just below it. */
function useHeaderHeight() {
  useEffect(() => {
    const header = document.querySelector<HTMLElement>('.club-header');
    if (!header || !('ResizeObserver' in window)) return;
    const root = document.documentElement;
    const observer = new ResizeObserver(() => root.style.setProperty('--header-h', `${header.offsetHeight}px`));
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
}

export default function Shell() {
  useLinkInterception();
  useHeaderHeight();
  const location = useLocation();
  const navigation = useNavigation();
  const {notices, error} = usePageMessages();
  return (
    <>
      <a className="skip" href="#main">К содержимому</a>
      <Header />
      <div className={'route-progress' + (navigation.state === 'loading' ? ' is-loading' : '')} aria-hidden="true" />
      <div className="shell">
        <main id="main">
          {/* keyed by path, so each page fades in; the sky and header stay put */}
          <div className="page" key={location.pathname}>
            {notices.length > 0 && (
              <div className="notices">{notices.map((n, i) => <div key={i} className={`notice ${n.kind}`} role="status">{n.text}</div>)}</div>
            )}
            {error ? <ErrorPage code={error.code} message={error.description} /> : <Outlet />}
          </div>
          <Footer />
        </main>
      </div>
      <InstantPageScroll />
      <ScrollRestoration getKey={scrollKey} />
    </>
  );
}
