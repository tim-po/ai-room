import type {ReactNode} from 'react';
import {Link} from 'react-router';

// Paths the React app renders. Anything else (admin, authoring, routes, assessments) is a server
// page and loads normally.
const SPA_PATHS = [
  /^\/$/, /^\/(profile|catalogue|membership|preferences|help|onboarding|login)$/,
  /^\/(lessons|courses|materials)\/[^/]+$/,
];
export const isSpaPath = (path: string) => SPA_PATHS.some(pattern => pattern.test(path));

/** Link that navigates inside the app for migrated pages and loads the page otherwise. */
export function AppLink({to, children, ...rest}: {to: string; children: ReactNode} & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'>) {
  const path = to.split(/[?#]/)[0];
  if (isSpaPath(path)) return <Link to={to} {...rest}>{children}</Link>;
  return <a href={to} {...rest}>{children}</a>;
}
