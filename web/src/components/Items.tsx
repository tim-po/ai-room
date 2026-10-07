import {Fragment, useEffect, useRef, useState, type ReactNode} from 'react';
import {plural} from '../format';
import {AppLink} from '../links';
import type {DiscoverItem, DiscoverTopic, ItemKind, Shelf} from '../types';

// Обзор: posters, shelves and the hero. Every item links to its page (coming ones to their place
// on the map); covers are generated art per topic, so nothing waits on images.

export const KIND_LABEL: Record<ItemKind, string> = {lesson: 'Урок', course: 'Курс', guide: 'Гайд', use_case: 'Кейс', workshop: 'Воркшоп', coming: 'Скоро'};

function Motif({topic}: {topic: string}) {
  return (
    <svg className="d-motif" viewBox="0 0 200 120" fill="none" aria-hidden="true" focusable="false">
      {topic === 'coding' ? (
        <><rect x="46" y="22" width="108" height="76" rx="12" /><path d="M46 42h108M60 32h2m8 0h2m8 0h2M88 58 74 70l14 12m24-24 14 12-14 12m-6-30-8 36" /></>
      ) : topic === 'content' ? (
        <><rect x="42" y="24" width="96" height="66" rx="12" /><path d="m80 45 22 12-22 12V45Z" /><rect x="112" y="52" width="48" height="44" rx="10" /><path d="m120 86 10-12 8 8 6-6 10 10" /><circle cx="146" cy="64" r="4" /></>
      ) : topic === 'agents' ? (
        <><circle cx="100" cy="60" r="16" /><circle cx="48" cy="34" r="9" /><circle cx="152" cy="34" r="9" /><circle cx="48" cy="88" r="9" /><circle cx="152" cy="88" r="9" /><path d="M57 38l29 14m28 0 29-14M57 84l29-14m28 0 29 14M94 56h.01M106 56h.01M94 66c4 3 8 3 12 0" /></>
      ) : (
        <><path d="M54 30h68a14 14 0 0 1 14 14v22a14 14 0 0 1-14 14H90l-18 14V80H54a14 14 0 0 1-14-14V44a14 14 0 0 1 14-14Z" /><path d="M58 50h44M58 62h30M156 24v18M147 33h18M164 64v12M158 70h12" /></>
      )}
    </svg>
  );
}

/** Poster art: a gradient per topic with a line motif. Decorative. */
export function Cover({item, topic}: {item?: DiscoverItem; topic?: string}) {
  const id = topic ?? item?.topic_id ?? 'basic-ai';
  return (
    <span className={`d-art topic-${id}${item ? ` kind-${item.kind}` : ''}`} aria-hidden="true">
      <Motif topic={id} />
    </span>
  );
}

export function kicker(item: DiscoverItem): string {
  if (item.kind === 'coming') return item.sub === 'lesson' ? 'Скоро · урок' : `Скоро · ${item.lessons} ${plural(item.lessons ?? 0, 'урок', 'урока', 'уроков')}`;
  if (item.kind === 'course') {
    const shown = item.catalog_total && item.catalog_total > (item.lessons ?? 0) ? item.catalog_total : item.lessons ?? 0;
    return `Курс · ${shown} ${plural(shown, 'урок', 'урока', 'уроков')}`;
  }
  return `${KIND_LABEL[item.kind]}${item.minutes ? ` · ${item.minutes} мин` : ''}`;
}

export function subline(item: DiscoverItem): string {
  if (item.course) return item.course.title;
  return [item.topic, item.level].filter(Boolean).join(' · ');
}

function Lock() {
  return <svg className="lock" viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" /><path d="M5.5 7V5.2a2.5 2.5 0 0 1 5 0V7" /></svg>;
}

export function Badges({item}: {item: DiscoverItem}) {
  const badges: ReactNode[] = [];
  if (item.state === 'done') badges.push(<span key="done" className="badge is-done">Пройдено</span>);
  else if (item.state === 'locked') badges.push(<span key="lock" className="badge is-club"><Lock />Клуб</span>);
  else if (item.state === 'progress' && item.kind === 'lesson') badges.push(<span key="prog" className="badge is-progress">Начат</span>);
  if (item.kind !== 'coming' && item.access === 'free' && item.state !== 'done') badges.push(<span key="free" className="badge is-free">Бесплатно</span>);
  if (item.new && item.state !== 'done') badges.push(<span key="new" className="badge is-new">Новое</span>);
  return badges.length ? <span className="badges">{badges}</span> : null;
}

/** Marks the query's stems in a title (е and ё match each other). */
export function highlight(text: string, stems: string[] = []): ReactNode {
  const words = stems.filter(s => s.length > 1).map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/е/g, '[её]'));
  if (!words.length) return text;
  const parts = text.split(new RegExp(`(${words.join('|')})`, 'gi'));
  return parts.map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : <Fragment key={i}>{part}</Fragment>));
}

function CourseProgress({item}: {item: DiscoverItem}) {
  if (item.kind !== 'course' || !item.done || !item.lessons) return null;
  return <span className="cover-progress" role="img" aria-label={`Пройдено ${item.done} из ${item.lessons}`}><span style={{width: `${(100 * item.done) / item.lessons}%`}} /></span>;
}

export function ItemCard({item, stems}: {item: DiscoverItem; stems?: string[]}) {
  return (
    <AppLink to={item.url} className={`d-card state-${item.state} kind-${item.kind}`}>
      <span className="d-cover"><Cover item={item} /><Badges item={item} /><CourseProgress item={item} /></span>
      <span className="d-body">
        <span className="d-kicker">{kicker(item)}</span>
        <strong className="d-title">{highlight(item.title, stems)}</strong>
        <span className="d-sub">{subline(item)}</span>
      </span>
    </AppLink>
  );
}

const RESUME: Record<string, string> = {draft: 'Черновик ждёт вас', started: 'Вы остановились здесь', next: 'Следующий урок'};

/** "Продолжить": a wide card with the course's progress. */
function WideCard({item}: {item: DiscoverItem}) {
  const total = item.course_total, done = item.course_done;
  return (
    <AppLink to={item.url + (item.resume === 'draft' ? '#practice' : '')} className="d-wide">
      <span className="d-cover"><Cover item={item} /></span>
      <span className="d-body">
        <span className="d-kicker">{RESUME[item.resume ?? 'next']}</span>
        <strong className="d-title">{item.title}</strong>
        <span className="d-sub">{item.course?.title}{item.minutes ? ` · ${item.minutes} мин` : ''}</span>
        {total ? <span className="d-meter" role="img" aria-label={`Курс: пройдено ${done} из ${total}`}><span style={{width: `${(100 * (done ?? 0)) / total}%`}} /></span> : null}
        <span className="d-action">Продолжить →</span>
      </span>
    </AppLink>
  );
}

/** Top in a topic: a big rank numeral beside a poster. */
function TopCard({item, rank}: {item: DiscoverItem; rank: number}) {
  return (
    <AppLink to={item.url} className={`d-top state-${item.state}`}>
      <span className="d-rank" aria-hidden="true">{rank}</span>
      <span className="d-poster">
        <Cover item={item} />
        <Badges item={item} />
        <span className="d-poster-text"><span className="d-kicker">{kicker(item)}</span><strong className="d-title">{item.title}</strong></span>
      </span>
      <span className="visually-hidden">Место {rank}</span>
    </AppLink>
  );
}

/** A horizontal shelf that scrolls by a page with the arrows (or by swipe / trackpad). */
export function ShelfRow({shelf}: {shelf: Shelf}) {
  const track = useRef<HTMLUListElement>(null);
  const [edge, setEdge] = useState({start: true, end: true});
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const update = () => setEdge({start: el.scrollLeft < 8, end: el.scrollLeft + el.clientWidth > el.scrollWidth - 8});
    update();
    el.addEventListener('scroll', update, {passive: true});
    const observer = 'ResizeObserver' in window ? new ResizeObserver(update) : null;
    observer?.observe(el);
    return () => { el.removeEventListener('scroll', update); observer?.disconnect(); };
  }, []);
  const page = (direction: number) => track.current?.scrollBy({left: direction * track.current.clientWidth * 0.85, behavior: 'smooth'});
  const titleId = `shelf-${shelf.id}`;
  return (
    <section className={`shelf shelf-${shelf.style}`} aria-labelledby={titleId}>
      <header className="shelf-head">
        <div>
          <h2 id={titleId}>{shelf.link ? <AppLink to={shelf.link}>{shelf.title}<span aria-hidden="true"> ›</span></AppLink> : shelf.title}</h2>
          {shelf.subtitle && <p>{shelf.subtitle}</p>}
        </div>
        {!(edge.start && edge.end) && (
          <span className="shelf-arrows">
            <button type="button" onClick={() => page(-1)} disabled={edge.start} aria-label={`${shelf.title}: назад`}>‹</button>
            <button type="button" onClick={() => page(1)} disabled={edge.end} aria-label={`${shelf.title}: дальше`}>›</button>
          </span>
        )}
      </header>
      <ul className="shelf-track" ref={track}>
        {shelf.items.map((item, i) => (
          <li key={(item.id ?? item.title) + i}>
            {shelf.style === 'top' ? <TopCard item={item} rank={i + 1} /> : shelf.style === 'wide' ? <WideCard item={item} /> : <ItemCard item={item} />}
          </li>
        ))}
      </ul>
    </section>
  );
}

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Up to three featured items; turns every 7 s unless the learner is pointing at or focused on it. */
export function Hero({items}: {items: DiscoverItem[]}) {
  const [index, setIndex] = useState(0);
  const [held, setHeld] = useState(false);
  useEffect(() => {
    if (items.length < 2 || held || reducedMotion()) return;
    const timer = setInterval(() => setIndex(i => (i + 1) % items.length), 7000);
    return () => clearInterval(timer);
  }, [items.length, held]);
  if (!items.length) return null;
  return (
    <section className="d-hero" aria-roledescription="карусель" aria-label="Рекомендуем"
      onPointerEnter={() => setHeld(true)} onPointerLeave={() => setHeld(false)} onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}>
      {items.map((item, i) => (
        <div key={(item.id ?? item.title) + i} className={'d-hero-slide' + (i === index ? ' is-active' : '')} aria-hidden={i !== index} inert={i !== index}
          aria-roledescription="слайд" aria-label={`${i + 1} из ${items.length}`}>
          <Cover item={item} />
          <div className="d-hero-copy">
            <span className="d-kicker">{item.resume ? RESUME[item.resume] : kicker(item)}{item.topic ? ` · ${item.topic}` : ''}</span>
            <h2>{item.title}</h2>
            {item.text && <p>{item.text}</p>}
            <div className="d-hero-meta">
              {item.course && <span>{item.course.title}</span>}
              {item.minutes ? <span>{item.minutes} мин</span> : null}
              {item.level && <span>{item.level}</span>}
              {item.access === 'free' && <span className="is-free">Бесплатно</span>}
            </div>
            <div className="d-hero-actions">
              <AppLink className="button" to={item.url + (item.resume === 'draft' ? '#practice' : '')}>{item.cta ?? 'Открыть'} →</AppLink>
              {item.course && <AppLink className="button secondary" to={`/courses/${item.course.id}`}>О курсе</AppLink>}
            </div>
          </div>
        </div>
      ))}
      {items.length > 1 && (
        <div className="d-hero-dots">
          {items.map((item, i) => (
            <button key={i} type="button" aria-label={`Слайд ${i + 1}: ${item.title}`} aria-current={i === index || undefined} onClick={() => setIndex(i)} />
          ))}
        </div>
      )}
    </section>
  );
}

export function TopicTiles({topics, active}: {topics: DiscoverTopic[]; active?: string}) {
  return (
    <ul className="topic-tiles">
      {topics.map(topic => (
        <li key={topic.id}>
          <AppLink to={`/discover?topic=${topic.id}`} className={'topic-tile' + (topic.id === active ? ' is-active' : '')} aria-current={topic.id === active || undefined}>
            <Cover topic={topic.id} />
            <strong>{topic.title}</strong>
            <span>{topic.subtitle}</span>
            <em>
              {topic.available ? `${topic.available} ${plural(topic.available, 'курс и урок', 'курса и урока', 'курсов и уроков')}` : 'Скоро'}
              {topic.interest && ' · ваш интерес'}
            </em>
          </AppLink>
        </li>
      ))}
    </ul>
  );
}
