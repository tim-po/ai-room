import {useState, type FormEvent} from 'react';
import {useLoaderData, useSearchParams, type LoaderFunctionArgs} from 'react-router';
import {bootstrap, getJson, withSearch} from '../api';
import Select from '../components/Select';
import {plural} from '../format';
import {AppLink} from '../Shell';
import type {CatalogueData, CourseCard, MaterialCard} from '../types';
import {useTitle} from '../useTitle';

export const catalogueLoader = ({request}: LoaderFunctionArgs) =>
  getJson<CatalogueData>(withSearch('/api/app/catalogue', request), request.signal);

const FILTERS = ['goal', 'level', 'format', 'tool'] as const;

/** Original line illustrations for the card covers; decorative only. */
function LibraryArt({goal}: {goal: string}) {
  return (
    <svg className="library-art" viewBox="0 0 300 140" fill="none" aria-hidden="true" focusable="false">
      {goal === 'build' ? (
        <><rect x="65" y="20" width="166" height="102" rx="9" /><path d="M65 42h166M82 31h3m7 0h3m7 0h3M114 63l-20 18 20 18m55-36 20 18-20 18m-22-40-15 45" /><rect x="209" y="71" width="40" height="60" rx="7" /><path d="M221 120h15" /></>
      ) : goal === 'agents' ? (
        <><path d="M95 71h45m38 0h44M159 53V25m0 64v29" /><circle cx="159" cy="71" r="19" /><rect x="48" y="51" width="47" height="40" rx="8" /><rect x="222" y="51" width="47" height="40" rx="8" /><path d="m61 71 7 7 14-14m150 7h23M145 25h28m-28 93h28" /><circle cx="159" cy="25" r="6" /><circle cx="159" cy="118" r="6" /></>
      ) : goal === 'work' ? (
        <><rect x="88" y="22" width="107" height="105" rx="8" /><path d="M107 44h52m-52 18h69m-69 18h37m-37 20h45" /><rect x="166" y="76" width="76" height="44" rx="8" /><path d="m184 98 10 9 19-20M66 36v26m-13-13h26" /></>
      ) : (
        <><path d="M151 27v86M91 47l60-20 60 20v58l-60 19-60-19V47Zm0 0 60 20 60-20M151 67v57" /><circle cx="151" cy="27" r="6" /><circle cx="91" cy="47" r="6" /><circle cx="211" cy="47" r="6" /><circle cx="151" cy="124" r="6" /><path d="M59 91h16m-8-8v16m171-55h16m-8-8v16" /></>
      )}
    </svg>
  );
}

function CourseCardView({course}: {course: CourseCard}) {
  const partial = course.catalog_total > course.total;
  return (
    <article className="card">
      <div className={`cover cover-${course.goal}`}><span>{course.topic}</span><LibraryArt goal={course.goal} /></div>
      <div className="card-body">
        <div className="metadata">
          {course.level} · {partial
            ? `открыто ${course.total} из ${course.catalog_total} ${plural(course.catalog_total, 'урока', 'уроков', 'уроков')}`
            : `${course.minutes} мин · ${course.total} ${plural(course.total, 'урок', 'урока', 'уроков')}`}
        </div>
        <h3><AppLink to={`/courses/${course.id}`}>{course.title}</AppLink></h3>
        <p>{course.description}</p>
        <span className="chip">{course.free === course.total ? 'Все уроки бесплатно' : 'Бесплатный старт · далее клуб'}</span>
        {bootstrap.user && (
          <>
            <div className="progress-label"><span>Пройдено</span><span>{course.done} / {course.total}</span></div>
            <progress value={course.done} max={course.total || 1}>{course.done} из {course.total}</progress>
          </>
        )}
      </div>
    </article>
  );
}

function MaterialCardView({item, formats}: {item: MaterialCard; formats: Record<string, string>}) {
  return (
    <article className="card">
      <div className={`cover cover-${item.goal}`}><span>{formats[item.format]}</span><LibraryArt goal={item.goal} /></div>
      <div className="card-body">
        <p className="metadata">{item.level} · {item.minutes} мин</p>
        <h3><AppLink to={`/materials/${item.id}`}>{item.title}</AppLink></h3>
        <p>{item.description}</p>
        <p>{item.outcome}</p>
        <span className="chip">{item.access === 'free' ? 'Бесплатно' : 'Материал клуба'}</span>
      </div>
    </article>
  );
}

function SearchForm({data}: {data: CatalogueData}) {
  const [params, setParams] = useSearchParams();
  // Form fields mirror the URL; submitting writes them back, which reloads the results.
  const [fields, setFields] = useState(() => ({
    q: params.get('q') ?? '', goal: params.get('goal') ?? '', level: params.get('level') ?? '',
    format: params.get('format') ?? '', tool: params.get('tool') ?? '',
  }));
  const set = (key: keyof typeof fields) => (value: string) => setFields(current => ({...current, [key]: value}));
  const activeFilters = FILTERS.filter(key => params.get(key)).length;
  function submit(event: FormEvent) {
    event.preventDefault();
    setParams(Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v)));
  }
  return (
    <form className="library-search" role="search" aria-label="Поиск по библиотеке" onSubmit={submit}>
      <div className="library-query">
        <label>Поиск<input type="search" name="q" value={fields.q} onChange={e => set('q')(e.target.value)} placeholder="Название, задача или инструмент" maxLength={150} /></label>
        <button className="button">Найти</button>
      </div>
      <details className="library-filters" open={activeFilters > 0 || undefined}>
        <summary>Фильтры{activeFilters > 0 && ` · выбрано ${activeFilters}`}</summary>
        <div className="library-filter-fields">
          <Select label="Цель" value={fields.goal} onChange={set('goal')} options={[['', 'Все цели'], ...data.filters.goals]} />
          <Select label="Уровень" value={fields.level} onChange={set('level')} options={[['', 'Любой'], ...data.filters.levels.map(l => [l, l] as const)]} />
          <Select label="Формат" value={fields.format} onChange={set('format')} options={[['', 'Все форматы'], ...data.filters.formats]} />
          <label>Инструмент<input type="search" name="tool" value={fields.tool} onChange={e => set('tool')(e.target.value)} maxLength={150} placeholder="Например, ChatGPT" /></label>
        </div>
        <button className="button secondary">Применить фильтры</button>
      </details>
      {(activeFilters > 0 || params.get('q')) && <AppLink className="library-reset" to="/catalogue">Сбросить всё</AppLink>}
    </form>
  );
}

export default function Catalogue() {
  const data = useLoaderData() as CatalogueData;
  const [params] = useSearchParams();
  useTitle('Библиотека');
  const formats = Object.fromEntries(data.filters.formats);
  const empty = !data.courses.length && !data.materials.length;
  return (
    <section className="library">
      <header className="page-intro"><span className="eyebrow">Библиотека AI Room</span><h1>От идеи к практике</h1><p>Уроки и материалы для вашей следующей задачи.</p></header>
      {/* keyed by the query so "Сбросить всё" and back/forward reset the fields */}
      <SearchForm key={params.toString()} data={data} />
      <p className="metadata library-count" role="status">
        Найдено: {data.courses.length + data.materials.length} · курсов: {data.courses.length} · материалов: {data.materials.length}
      </p>
      {data.courses.length > 0 && <><h2>Курсы</h2><div className="grid cards">{data.courses.map(c => <CourseCardView key={c.id} course={c} />)}</div></>}
      {data.coming.length > 0 && (
        <section className="coming" aria-labelledby="coming-title">
          <h2 id="coming-title">Скоро в AI Room</h2>
          <p>Эти курсы уже есть на карте навыков. Уроки появятся здесь по мере переноса.</p>
          <div className="coming-grid">
            {data.coming.map(c => (
              <AppLink key={c.id} className="coming-card" to={`/?view=map#course-${c.id}`}>
                <span className="coming-topic">{c.topic} · {c.level}</span>
                <strong>{c.title}</strong>
                <span className="coming-meta">
                  {c.modules} {plural(c.modules, 'модуль', 'модуля', 'модулей')}
                  {c.total != null && <> · {c.total} {plural(c.total, 'урок', 'урока', 'уроков')}</>}
                </span>
                <span className="coming-link">Посмотреть на карте →</span>
              </AppLink>
            ))}
          </div>
        </section>
      )}
      {data.materials.length > 0 && <><h2>Гайды, кейсы и воркшопы</h2><div className="grid cards">{data.materials.map(m => <MaterialCardView key={m.id} item={m} formats={formats} />)}</div></>}
      {empty && <section className="panel"><h2>Ничего не найдено</h2><p>Попробуйте другой запрос или уберите фильтры.</p><AppLink to="/catalogue">Сбросить фильтры</AppLink></section>}
    </section>
  );
}
