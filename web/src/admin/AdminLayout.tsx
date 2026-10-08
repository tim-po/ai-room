import type {ReactNode} from 'react';
import {Link, NavLink, Outlet} from 'react-router';
import {bootstrap} from '../api';

const icon = (d: string) => <svg viewBox="0 0 24 24" aria-hidden="true"><path d={d} /></svg>;

const SECTIONS: {to: string; label: string; icon: ReactNode; admin?: boolean; end?: boolean}[] = [
  {to: '/admin', label: 'Обзор', end: true, icon: icon('M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-3H4zM14 7h6V4h-6z')},
  {to: '/admin/courses', label: 'Курсы и уроки', icon: icon('M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5zM13 4h5.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H13z')},
  {to: '/admin/library', label: 'Библиотека', icon: icon('M5 4h4v16H5zM10.5 4h4v16h-4zM16 5l3.6-.8 3 15.6-3.6.8z')},
  {to: '/admin/questions', label: 'Вопросы', icon: icon('M5 5h14v10H9l-4 4z')},
  {to: '/admin/works', label: 'Работы', icon: icon('M6 3h9l4 4v14H6zM14 3v5h5M9 13l2 2 4-4')},
  {to: '/admin/learners', label: 'Ученики', admin: true, icon: icon('M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.3a3.5 3.5 0 0 1 0 6.4M18 14.2a6.5 6.5 0 0 1 3.5 5.8')},
  {to: '/admin/analytics', label: 'Аналитика', admin: true, icon: icon('M4 20V10M10 20V4M16 20v-7M22 20H2')},
];

export default function AdminLayout() {
  const role = bootstrap.user?.role;
  return (
    <div className="adm">
      <aside className="adm-side" aria-label="Разделы админки">
        <Link to="/admin" className="adm-side-title">
          <span className="adm-side-mark" aria-hidden="true">AR</span>
          <span><strong>Админка</strong><small>{role === 'admin' ? 'Администратор' : 'Редактор'}</small></span>
        </Link>
        <nav>
          {SECTIONS.filter(s => !s.admin || role === 'admin').map(s => (
            <NavLink key={s.to} to={s.to} end={s.end} className={({isActive}) => 'adm-nav' + (isActive ? ' is-active' : '')}>
              {s.icon}<span>{s.label}</span>
            </NavLink>
          ))}
        </nav>
        <a className="adm-back" href="/">← К платформе</a>
      </aside>
      <div className="adm-main">
        <Outlet />
      </div>
    </div>
  );
}
