import {prefetchJson} from './api';
import {isSpaPath} from './links';

// Which API a page's loader reads (club/spa.py page_data_url mirrors this), so a link's data can be
// fetched before the learner clicks it.

const SEARCH = ['q', 'class', 'topic', 'level', 'access'];
const FIXED: Record<string, string> = {
  '/': '/api/app/home', '/map': '/api/app/home', '/profile': '/api/app/profile', '/preferences': '/api/app/preferences',
  '/onboarding': '/api/onboarding', '/oauth/consent': '/api/app/oauth/consent',
};

export function pageDataUrl(pathname: string, search: string): string | null {
  if (FIXED[pathname]) return FIXED[pathname];
  if (pathname === '/discover' || pathname === '/catalogue') {
    const params = new URLSearchParams(search);
    return SEARCH.some(key => params.get(key)) ? '/api/app/search' + search : '/api/app/discover';
  }
  if (pathname === '/membership' || pathname === '/help') return '/api/app' + pathname + search;
  if (pathname === '/admin') return '/api/admin/overview';
  if (/^\/admin\/((courses|lessons|library|learners)(\/[A-Za-z0-9_.-]+)?|questions|works|analytics)$/.test(pathname)) return '/api' + pathname + search;
  const match = /^\/(lessons|courses|materials)\/([A-Za-z0-9_.-]+)$/.exec(pathname);
  return match ? `/api/app/${match[1]}/${match[2]}` : null;
}

export function prefetchPage(href: string) {
  const url = new URL(href, window.location.href);
  if (url.origin !== window.location.origin || !isSpaPath(url.pathname)) return;
  if (url.pathname === window.location.pathname && url.search === window.location.search) return;
  const api = pageDataUrl(url.pathname, url.search);
  if (api) prefetchJson(api);
}
