import {useEffect, useRef, useState} from 'react';
import {useLocation} from 'react-router';
import {getJson} from '../api';
import {AppLink} from '../links';

// «Мои курсы» in the header: the lesson to continue, then the courses you've started, newest first
// (/api/app/my-courses). Loaded when first opened; closes on a click elsewhere, Escape or navigation.

interface MyCourse {id: string; title: string; done: number; total: number; url: string; next: {title: string; url: string} | null}
interface MyCoursesData {continue_: {title: string; url: string; status?: string} | null; courses: MyCourse[]}

export default function MyCourses({active}: {active: boolean}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<MyCoursesData | null>(null);
  const [failed, setFailed] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const {pathname} = useLocation();
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    if (!data) getJson<MyCoursesData>('/api/app/my-courses').then(setData, () => setFailed(true));
    const away = (event: Event) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); root.current?.querySelector('button')?.focus(); } };
    document.addEventListener('pointerdown', away);
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', key); };
  }, [open, data]);
  return (
    <div className="my-courses" ref={root}>
      <button type="button" className="my-courses-button" aria-expanded={open} aria-haspopup="true" aria-current={active ? 'page' : undefined}
        onClick={() => setOpen(o => !o)}>
        Мои курсы<svg viewBox="0 0 12 12" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
      </button>
      {open && (
        <div className="my-courses-panel" role="dialog" aria-label="Мои курсы">
          {!data ? <p className="my-courses-note">{failed ? 'Не удалось загрузить. Попробуйте ещё раз.' : 'Загружаю…'}</p> : <>
            {data.continue_ && (
              <AppLink className="my-courses-continue" to={data.continue_.url + (data.continue_.status === 'draft' ? '#practice' : '')}>
                <small>{data.continue_.status === 'draft' ? 'Черновик ждёт вас' : 'Продолжить'}</small>
                <strong>{data.continue_.title}</strong>
              </AppLink>
            )}
            {data.courses.length ? (
              <ul>
                {data.courses.map(c => (
                  <li key={c.id}>
                    <AppLink to={c.url}>
                      <span className="my-courses-title">{c.title}</span>
                      <span className="my-courses-meter" aria-hidden="true"><span style={{width: `${c.total ? (c.done / c.total) * 100 : 0}%`}} /></span>
                      <small>{c.done} из {c.total}{c.next ? ` · дальше «${c.next.title}»` : ''}</small>
                    </AppLink>
                  </li>
                ))}
              </ul>
            ) : <p className="my-courses-note">Вы ещё не начали ни одного курса. Выберите первый в Обзоре или на карте.</p>}
            <AppLink className="my-courses-all" to="/profile">Весь прогресс в профиле →</AppLink>
          </>}
        </div>
      )}
    </div>
  );
}
