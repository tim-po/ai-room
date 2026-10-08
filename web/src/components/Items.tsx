import {Fragment, useEffect, useRef, useState, type ReactNode} from 'react';
import {plural} from '../format';
import {AppLink} from '../links';
import type {DiscoverItem, DiscoverTopic, ItemKind, Shelf} from '../types';

// Обзор: posters, shelves and the hero. Every item links to its page (coming ones to their place
// on the map); covers are type on a topic colour, so nothing waits on images.

export const KIND_LABEL: Record<ItemKind, string> = {lesson: 'Урок', course: 'Курс', guide: 'Гайд', use_case: 'Кейс', workshop: 'Воркшоп', coming: 'Скоро'};

const GENERIC = new Set(['AI', 'PRO', 'ИИ']);

/** The word a cover is set in: the tool the item is about (Claude, ChatCut…), else its topic. */
function coverWord(item: DiscoverItem): string {
  for (const text of [item.title, item.course?.title ?? '']) {
    const word = (text.match(/[A-Za-z][A-Za-z0-9.+-]{2,}/g) ?? []).find(w => !GENERIC.has(w.toUpperCase()));
    if (word) return word;
  }
  return item.topic ?? '';
}

/** Poster art: a flat topic colour with the item's word set large and cropped. Decorative. */
export function Cover({item, topic}: {item?: DiscoverItem; topic?: string}) {
  const id = topic ?? item?.topic_id ?? 'basic-ai';
  const word = item ? coverWord(item) : '';
  return (
    <span className={`d-art topic-${id}${item ? ` kind-${item.kind}` : ''}`} aria-hidden="true">
      {word && <span className="d-word">{word}</span>}
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

/** One badge per card: the state first, then «Бесплатно», then «Новое». */
export function Badges({item}: {item: DiscoverItem}) {
  const badge = item.state === 'done' ? <span className="badge is-done">Пройдено</span>
    : item.state === 'locked' ? <span className="badge is-club"><Lock />Клуб</span>
    : item.state === 'progress' && item.kind === 'lesson' ? <span className="badge is-progress">Начат</span>
    : item.kind !== 'coming' && item.access === 'free' ? <span className="badge is-free">Бесплатно</span>
    : item.new ? <span className="badge is-new">Новое</span>
    : null;
  return badge ? <span className="badges">{badge}</span> : null;
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

function heroMeta(item: DiscoverItem): string[] {
  if (item.kind === 'course') {
    const total = item.catalog_total ?? item.lessons ?? 0;
    return [total > (item.lessons ?? 0) ? `Открыто ${item.lessons ?? 0} из ${total} уроков` : `${total} ${plural(total, 'урок', 'урока', 'уроков')}`, item.level ?? ''].filter(Boolean);
  }
  return [item.course?.title ?? '', item.minutes ? `${item.minutes} мин` : '', item.level ?? ''].filter(Boolean);
}

/** Featured items as a strip of large cards: swipe, scroll or use the arrows; nothing moves by itself. */
export function Hero({items}: {items: DiscoverItem[]}) {
  const track = useRef<HTMLUListElement>(null);
  const [index, setIndex] = useState(0);
  // Where the track scrolls to bring a slide to its start (the track is the slides' offset parent).
  const stop = (el: HTMLElement, slide: Element) => (slide as HTMLElement).offsetLeft - parseFloat(getComputedStyle(el).scrollPaddingLeft || '0');
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const update = () => {
      const distances = Array.from(el.children, slide => Math.abs(stop(el, slide) - el.scrollLeft));
      setIndex(distances.indexOf(Math.min(...distances)));
    };
    el.addEventListener('scroll', update, {passive: true});
    return () => el.removeEventListener('scroll', update);
  }, []);
  if (!items.length) return null;
  const go = (i: number) => {
    const el = track.current, slide = el?.children[i];
    if (el && slide) el.scrollTo({left: stop(el, slide), behavior: 'smooth'});
  };
  return (
    <section className={'d-hero' + (items.length === 1 ? ' is-single' : '')} aria-label="Рекомендуем">
      <ul className="d-hero-track" ref={track}>
        {items.map((item, i) => (
          <li key={(item.id ?? item.title) + i} className="d-hero-slide" aria-label={`${i + 1} из ${items.length}`}>
            <Cover item={item} />
            <div className="d-hero-copy">
              <span className="d-kicker">{item.resume ? RESUME[item.resume] : KIND_LABEL[item.kind]}{item.topic ? ` · ${item.topic}` : ''}</span>
              <h2>{item.title}</h2>
              {item.text && <p>{item.text}</p>}
              <p className="d-hero-meta">
                {heroMeta(item).join(' · ')}
                {item.access === 'free' && <span className="is-free">Бесплатно</span>}
              </p>
              <div className="d-hero-actions">
                <AppLink className="button" to={item.url + (item.resume === 'draft' ? '#practice' : '')}>{item.cta ?? 'Открыть'} →</AppLink>
                {item.course && <AppLink className="button secondary" to={`/courses/${item.course.id}`}>О курсе</AppLink>}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {items.length > 1 && (
        <div className="d-hero-nav">
          <span className="d-hero-dots">
            {items.map((item, i) => (
              <button key={i} type="button" aria-label={`Показать: ${item.title}`} aria-current={i === index || undefined} onClick={() => go(i)} />
            ))}
          </span>
          <span className="shelf-arrows">
            <button type="button" onClick={() => go(index - 1)} disabled={index === 0} aria-label="Рекомендуем: назад">‹</button>
            <button type="button" onClick={() => go(index + 1)} disabled={index === items.length - 1} aria-label="Рекомендуем: дальше">›</button>
          </span>
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
              {topic.available ? `${topic.available} ${plural(topic.available, 'материал', 'материала', 'материалов')}` : 'Скоро'}
              {topic.available && topic.coming ? ` · ещё ${topic.coming} скоро` : ''}
              {topic.interest && ' · ваш интерес'}
            </em>
          </AppLink>
        </li>
      ))}
    </ul>
  );
}
