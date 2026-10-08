import {useLoaderData, useSearchParams, type LoaderFunctionArgs} from 'react-router';
import {getJson} from '../api';
import {Hero, ItemCard, ShelfRow, TopicTiles} from '../components/Items';
import {SearchBox} from '../components/Search';
import {plural} from '../format';
import {AppLink} from '../links';
import type {DiscoverData, ItemKind, SearchData} from '../types';
import {useTitle} from '../useTitle';

// Обзор: a store front for learning. Without a query it is shelves (continue, free to start, top
// per topic, classes, quick lessons, coming); with a query, a class or a topic it is a filterable
// grid. /catalogue shows the same page, so old links keep working.

const FILTERS = ['q', 'class', 'topic', 'level', 'access'] as const;

type Loaded = {mode: 'home'; data: DiscoverData} | {mode: 'results'; data: SearchData};

export async function discoverLoader({request}: LoaderFunctionArgs): Promise<Loaded> {
  const url = new URL(request.url);
  if (FILTERS.some(key => url.searchParams.get(key))) {
    return {mode: 'results', data: await getJson<SearchData>('/api/app/search' + url.search, request.signal)};
  }
  return {mode: 'home', data: await getJson<DiscoverData>('/api/app/discover', request.signal)};
}

/** The current filters with one changed (empty removes it). */
function useFilterLink() {
  const [params] = useSearchParams();
  return (key: string, value: string) => {
    const next = new URLSearchParams();
    for (const k of FILTERS) if (params.get(k)) next.set(k, params.get(k)!);
    if (value) next.set(key, value); else next.delete(key);
    const query = next.toString();
    return '/discover' + (query ? `?${query}` : '');
  };
}

function ClassChips({classes, current}: {classes: {id: ItemKind; title: string; count: number}[]; current: string}) {
  const link = useFilterLink();
  return (
    <nav className="chip-row" aria-label="Разделы">
      <AppLink to={link('class', '')} className="chip-link" aria-current={!current || undefined}>Всё</AppLink>
      {classes.map(c => (
        <AppLink key={c.id} to={link('class', c.id)} className="chip-link" aria-current={current === c.id || undefined}>
          {c.title}<span>{c.count}</span>
        </AppLink>
      ))}
    </nav>
  );
}

function Results({data}: {data: SearchData}) {
  const [params] = useSearchParams();
  const link = useFilterLink();
  const q = params.get('q') ?? '', kind = params.get('class') ?? '', topicId = params.get('topic') ?? '', free = params.get('access') === 'free';
  const topic = data.topics.find(t => t.id === topicId);
  const className = data.classes.find(c => c.id === kind)?.title;
  const title = q ? `«${q}»` : topic ? topic.title : className ?? 'Всё';
  useTitle(q ? `Поиск: ${q}` : title);
  const ready = data.items.filter(i => i.kind !== 'coming');
  const coming = data.items.filter(i => i.kind === 'coming');
  return (
    <>
      <header className="results-head">
        <p className="eyebrow">{q ? 'Поиск' : topic ? 'Направление' : 'Раздел'}</p>
        <h2>{title}</h2>
        {topic && !q && <p className="results-sub">{topic.subtitle}</p>}
        <p className="results-count" role="status">
          {data.total ? `${data.total} ${plural(data.total, 'результат', 'результата', 'результатов')}` : 'Ничего не найдено'}
        </p>
      </header>
      <div className="filter-bar">
        <nav className="chip-row is-small" aria-label="Направление">
          <AppLink to={link('topic', '')} className="chip-link" aria-current={!topicId || undefined}>Все направления</AppLink>
          {data.topics.map(t => <AppLink key={t.id} to={link('topic', t.id)} className="chip-link" aria-current={topicId === t.id || undefined}>{t.title}</AppLink>)}
        </nav>
        <AppLink to={link('access', free ? '' : 'free')} className="chip-link is-toggle" aria-pressed={free} role="button">Только бесплатное</AppLink>
      </div>
      {ready.length > 0 && <ul className="result-grid">{ready.map((item, i) => <li key={(item.id ?? item.title) + i}><ItemCard item={item} stems={data.stems} /></li>)}</ul>}
      {coming.length > 0 && (
        <section className="results-coming" aria-labelledby="results-coming">
          <h3 id="results-coming">Скоро на платформе</h3>
          <p>Эти уроки уже есть на карте навыков и появятся здесь по мере переноса.</p>
          <ul className="result-grid is-compact">{coming.map((item, i) => <li key={item.title + i}><ItemCard item={item} stems={data.stems} /></li>)}</ul>
        </section>
      )}
      {!data.total && (
        <section className="results-empty">
          <p>Попробуйте другое слово или посмотрите, что уже есть:</p>
          <div className="chip-row">
            {data.suggestions.map(s => <AppLink key={s} to={`/discover?q=${encodeURIComponent(s)}`} className="chip-link">{s}</AppLink>)}
          </div>
          <AppLink to="/discover" className="button secondary">Весь обзор</AppLink>
        </section>
      )}
    </>
  );
}

function Home({data}: {data: DiscoverData}) {
  useTitle('Обзор');
  // Topics come after the first rows: first what to do now, then where to go.
  const split = data.shelves.findIndex(s => s.style === 'top');
  const before = split < 0 ? data.shelves : data.shelves.slice(0, split);
  const after = split < 0 ? [] : data.shelves.slice(split);
  return (
    <>
      <Hero items={data.hero} />
      {before.map(shelf => <ShelfRow key={shelf.id} shelf={shelf} />)}
      <section className="shelf" aria-labelledby="topics-title">
        <header className="shelf-head"><div><h2 id="topics-title">Направления</h2><p>Всё, что есть, и что скоро появится, — по темам</p></div></header>
        <TopicTiles topics={data.topics} />
      </section>
      {after.map(shelf => <ShelfRow key={shelf.id} shelf={shelf} />)}
    </>
  );
}

export default function Discover() {
  const loaded = useLoaderData() as Loaded;
  const [params] = useSearchParams();
  return (
    <div className="discover">
      <header className="discover-head">
        <h1>Обзор</h1>
        {/* keyed by the query, so going back to the shelves clears the field */}
        <SearchBox key={params.get('q') ?? ''} variant="inline" initial={params.get('q') ?? ''} />
        <ClassChips classes={loaded.data.classes} current={params.get('class') ?? ''} />
      </header>
      {loaded.mode === 'home' ? <Home data={loaded.data} /> : <Results data={loaded.data} />}
    </div>
  );
}
