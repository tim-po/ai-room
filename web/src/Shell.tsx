import {useEffect, type ReactNode} from 'react';
import {Link, Outlet, ScrollRestoration, useLocation, useNavigate, useNavigation} from 'react-router';
import {bootstrap} from './api';

// Paths the React app renders. Anything else is a server page and loads normally.
const SPA_PATHS = [/^\/$/, /^\/profile$/, /^\/lessons\/[^/]+$/];
export const isSpaPath = (path: string) => SPA_PATHS.some(pattern => pattern.test(path));

/** Link that navigates inside the app for migrated pages and loads the page otherwise. */
export function AppLink({to, children, ...rest}: {to: string; children: ReactNode} & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'>) {
  const path = to.split(/[?#]/)[0];
  if (isSpaPath(path)) return <Link to={to} {...rest}>{children}</Link>;
  return <a href={to} {...rest}>{children}</a>;
}

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
        <NavLink to="/catalogue" active={pathname.startsWith('/lessons/')}>Библиотека</NavLink>
        <NavLink to="/profile" active={pathname === '/profile'}>Моё обучение</NavLink>
        <NavLink to="/membership" active={false}>Клуб</NavLink>
        {user && user.role !== 'learner' && <a href="/admin">Мастерская</a>}
      </nav>
      <div className="header-account">
        <ThemeToggle />
        <a href={user ? '/help' : '/login'}>{user ? 'Помощь' : 'Войти'}</a>
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

export default function Shell() {
  useLinkInterception();
  const location = useLocation();
  const navigation = useNavigation();
  return (
    <>
      <a className="skip" href="#main">К содержимому</a>
      <Header />
      <div className={'route-progress' + (navigation.state === 'loading' ? ' is-loading' : '')} aria-hidden="true" />
      <div className="shell">
        <main id="main">
          {/* keyed by path, so each page fades in; the sky and header stay put */}
          <div className="page" key={location.pathname}>
            <Outlet />
          </div>
          <Footer />
        </main>
      </div>
      <ScrollRestoration />
    </>
  );
}
