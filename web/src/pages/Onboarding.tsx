import {useEffect, useRef, useState, type ReactNode} from 'react';
import {useLoaderData, useLocation, useNavigate, useNavigationType, type LoaderFunctionArgs, type ShouldRevalidateFunctionArgs} from 'react-router';
import {bootstrap, getJson} from '../api';
import {AppLink, isSpaPath} from '../Shell';
import type {OnboardingState, OnboardingStep} from '../types';
import {useTitle} from '../useTitle';

// Optional onboarding v1 (club/onboarding.py). Every step is saved on the server with a revision
// and an idempotency key; browser back/forward walks the steps by asking the server to move.

export const onboardingLoader = ({request}: LoaderFunctionArgs) => getJson<OnboardingState>('/api/onboarding', request.signal);
/** Steps are pushed onto history as the learner moves; those entries share the URL and don't refetch. */
export const onboardingShouldRevalidate = ({currentUrl, nextUrl, defaultShouldRevalidate}: ShouldRevalidateFunctionArgs) =>
  currentUrl.pathname === nextUrl.pathname && currentUrl.search === nextUrl.search ? false : defaultShouldRevalidate;

const STEPS: OnboardingStep[] = ['welcome', 'interests', 'pace', 'start'];
const BRANCHES: [string, string][] = [['basic-ai', 'Основы: Claude и ChatGPT'], ['coding', 'Код: сайты и инструменты'], ['content', 'Контент: картинки и видео'], ['agents', 'ИИ-агенты']];
const BRANCH_IDS = new Set(BRANCHES.map(([id]) => id));
type Action = 'save' | 'back' | 'next' | 'complete' | 'skip' | 'edit' | 'cancel';

interface Form {
  interests: string[];
  experience: string;
  minutes: string;
}
const formOf = (state: OnboardingState): Form => ({
  interests: state.draft.interests.filter(id => BRANCH_IDS.has(id)),
  experience: state.draft.experience ?? '',
  minutes: state.draft.available_minutes ? String(state.draft.available_minutes) : '',
});

function draftFor(state: OnboardingState, form: Form) {
  if (state.step === 'interests') return {interests: [...state.draft.interests.filter(id => !BRANCH_IDS.has(id)), ...form.interests]};
  if (state.step === 'pace') return {experience: form.experience || null, available_minutes: Number(form.minutes) || null};
  return {};
}

function reason(r: NonNullable<OnboardingState['recommendation']>) {
  const parts: string[] = [];
  const branch = BRANCHES.find(([id]) => id === r.branch)?.[1];
  if (r.reasons.includes('interest') && branch) parts.push(`Под ваш интерес «${branch}»`);
  else if (r.reasons.includes('foundation')) parts.push('Общая основа для любого направления');
  if (r.reasons.includes('level')) parts.push('для начинающих');
  if (r.minutes) parts.push(`${r.minutes} минут` + (r.reasons.includes('time') ? ' — укладывается в ваше время' : ''));
  return parts.join(' · ');
}

function Choices({legend, name, options, selected, multiple, disabled, onChange}: {
  legend: string; name: string; options: [string, string][]; selected: string | string[]; multiple?: boolean; disabled: boolean;
  onChange: (value: string, checked: boolean) => void;
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      {options.map(([value, label]) => (
        <label key={value} className="onboarding-choice">
          <input type={multiple ? 'checkbox' : 'radio'} name={name} value={value} disabled={disabled}
            checked={Array.isArray(selected) ? selected.includes(value) : selected === value}
            onChange={event => onChange(value, event.target.checked)} />
          <span>{label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export default function Onboarding() {
  const initial = useLoaderData() as OnboardingState;
  const navigate = useNavigate();
  const location = useLocation();
  const navigationType = useNavigationType();
  useTitle('Ваше начало');

  const [state, setState] = useState(initial);
  const [form, setForm] = useState(() => formOf(initial));
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [status, setStatus] = useState<ReactNode>('');
  // Async step walks (back/forward) read the latest values, not a render's snapshot.
  const stateRef = useRef(state), formRef = useRef(form), busyRef = useRef(false);
  const pending = useRef<{signature: string; payload: object} | null>(null);
  const title = useRef<HTMLHeadingElement>(null), statusRef = useRef<HTMLParagraphElement>(null), footer = useRef<HTMLDivElement>(null);
  const focusTitle = useRef(false);

  function apply(next: OnboardingState) {
    stateRef.current = next; setState(next);
    const nextForm = formOf(next);
    formRef.current = nextForm; setForm(nextForm);
  }
  function edit(change: Partial<Form>) {
    const next = {...formRef.current, ...change};
    formRef.current = next; setForm(next);
    setStatus('Есть несохранённые изменения. Сохраните выбор, чтобы продолжить.');
  }
  function go(destination: string) {
    if (isSpaPath(destination.split(/[?#]/)[0])) navigate(destination);
    else window.location.assign(destination);
  }
  function report(message: ReactNode) {
    setStatus(message);
    requestAnimationFrame(() => statusRef.current?.focus());
  }

  async function send(action: Action, extra: object = {}, destination: string | null = null, recordHistory = true): Promise<boolean> {
    if (busyRef.current) return false;
    busyRef.current = true; setBusy(true);
    const current = stateRef.current;
    const payload = {action, expected_revision: current.revision,
      draft: ['edit', 'cancel', 'skip'].includes(action) ? {} : {...draftFor(current, formRef.current), ...extra}};
    const signature = JSON.stringify(payload);
    // A retry of the same request reuses its key, so a save the server already applied isn't applied twice.
    if (!pending.current || pending.current.signature !== signature) pending.current = {signature, payload: {...payload, idempotency_key: crypto.randomUUID()}};
    setStatus('Сохраняем…');
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/onboarding', {method: 'PUT', signal: controller.signal,
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': bootstrap.csrf}, body: JSON.stringify(pending.current.payload)});
      if (response.status === 401) {
        report(<>Сессия завершена. Войдите снова: сохранённые шаги останутся в аккаунте. <AppLink to="/login?next=/onboarding">Войти снова</AppLink></>);
        return false;
      }
      let data: OnboardingState;
      try {
        data = await response.json();
      } catch (error) {
        if ((error as Error).name === 'AbortError') throw error;
        report('Сервер не подтвердил сохранение. Ваш выбор остаётся на экране. Повторите действие.');
        return false;
      }
      if (response.status === 409) {
        pending.current = null;
        setConflict(true);
        report(<>Настройки изменились в другой вкладке. Загрузите сохранённую версию перед продолжением.{' '}
          <button type="button" className="link-button" onClick={() => window.location.reload()}>Загрузить сохранённую версию</button></>);
        return false;
      }
      if (!response.ok) {
        report('Не удалось сохранить. Ваш выбор остаётся на экране. Повторите действие.');
        return false;
      }
      pending.current = null;
      apply(data);
      setStatus('');
      if (action === 'complete' || action === 'skip' || action === 'cancel') {
        go(destination || data.next_url || '/');
        return true;
      }
      if (recordHistory) navigate(location.pathname, {state: {onboardingStep: data.step}});
      focusTitle.current = true;
      return true;
    } catch (error) {
      report((error as Error).name === 'AbortError'
        ? 'Сервер пока не подтвердил сохранение. Ваш выбор остаётся на экране. Повторите действие.'
        : 'Нет связи с сервером. Ваш выбор остаётся на экране. Повторите действие.');
      return false;
    } finally {
      clearTimeout(timeout);
      busyRef.current = false; setBusy(false);
    }
  }

  useEffect(() => {
    if (!focusTitle.current) return;
    focusTitle.current = false;
    title.current?.focus();
  }, [state]);

  // History holds the step only (never revisions or request bodies).
  useEffect(() => {
    navigate(location.pathname, {replace: true, state: {onboardingStep: stateRef.current.step}});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    const target = (location.state as {onboardingStep?: OnboardingStep} | null)?.onboardingStep;
    if (navigationType !== 'POP' || !target || !STEPS.includes(target) || target === stateRef.current.step) return;
    if (busyRef.current || pending.current) {
      navigate(location.pathname, {state: {onboardingStep: stateRef.current.step}});
      if (!busyRef.current) setStatus('Сначала повторите сохранение текущего шага: сервер ещё не подтвердил его.');
      return;
    }
    // Each step on the way is a new request with the current choices and revision.
    (async () => {
      while (stateRef.current.step !== target) {
        const action = STEPS.indexOf(target) < STEPS.indexOf(stateRef.current.step) ? 'back' : 'next';
        if (!await send(action, {}, null, false)) {
          navigate(location.pathname, {replace: true, state: {onboardingStep: stateRef.current.step}});
          break;
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);

  // Keep focused fields clear of the sticky footer.
  useEffect(() => {
    if (!footer.current) return;
    const root = document.documentElement;
    const observer = new ResizeObserver(() => { root.style.scrollPaddingBottom = `${(footer.current?.offsetHeight ?? 0) + 24}px`; });
    observer.observe(footer.current);
    return () => { observer.disconnect(); root.style.scrollPaddingBottom = ''; };
  }, []);

  const locked = busy || conflict;
  const button = (text: string, onClick: () => void, style: 'primary' | 'secondary' | 'quiet' = 'primary') => (
    <button key={text} type="button" disabled={locked} onClick={onClick}
      className={style === 'quiet' ? 'link-button' : style === 'secondary' ? 'button secondary' : 'button'}>{text}</button>
  );

  const done = (state.status === 'completed' || state.status === 'skipped') && !state.editing;
  const index = done ? -1 : STEPS.indexOf(state.step);
  let heading: string, progress: string;
  const body: ReactNode[] = [], actions: ReactNode[] = [];

  if (done) {
    heading = 'Ваше начало — в вашем темпе';
    progress = 'Настройки обучения';
    body.push(<p key="p">Можно изменить интересы и время. Уроки, работы и результаты сохранятся.</p>);
    actions.push(button('Изменить интересы и темп', () => send('edit')),
      <AppLink key="back" to={state.return_to || '/'}>Вернуться к обучению</AppLink>,
      <AppLink key="prefs" to="/preferences">Недельная цель и аккаунт</AppLink>);
  } else {
    progress = `${state.editing ? 'Настройки · ' : ''}Шаг ${index + 1} из 4`;
    if (state.step === 'welcome') {
      heading = 'Небольшой шаг. Полезный результат.';
      body.push(<p key="a">Разберите одну идею, попробуйте её на своей задаче и сохраните работу. Здесь можно учиться сразу в нескольких направлениях.</p>,
        <p key="b">Пара необязательных вопросов поможет сохранить ваши пожелания. Их можно изменить позже.</p>);
    } else if (state.step === 'interests') {
      heading = 'Что хочется попробовать?';
      body.push(<p key="p">Выберите несколько направлений или ни одного. Вся карта останется открытой.</p>,
        <Choices key="c" legend="Ваши интересы" name="interests" multiple options={BRANCHES} selected={form.interests} disabled={locked}
          onChange={(value, checked) => edit({interests: checked ? [...formRef.current.interests, value] : formRef.current.interests.filter(i => i !== value)})} />);
    } else if (state.step === 'pace') {
      heading = 'Сколько места для нового?';
      body.push(
        <Choices key="e" legend="Опыт работы с ИИ" name="experience" disabled={locked} selected={form.experience}
          options={[['', 'Пока не хочу выбирать'], ['beginner', 'Начинаю разбираться'], ['experienced', 'Уже использую в работе']]}
          onChange={value => edit({experience: value})} />,
        <Choices key="m" legend="Время на один подход" name="minutes" disabled={locked} selected={form.minutes}
          options={[['', 'Без плана'], ['5', '5 минут'], ['10', '10 минут'], ['20', '20 минут']]}
          onChange={value => edit({minutes: value})} />,
        <p key="p">Это пожелание, а не обязательство. Пропуски не обнуляют обучение.</p>);
    } else {
      heading = 'Начните с одной идеи';
      body.push(<p key="p">Этот доступный урок — отправная точка. Это не оценка ваших знаний и не ограничение выбранными интересами.</p>);
      const pick = state.recommendation;
      if (pick) {
        const returning = !!state.return_to && state.return_to !== '/';
        body.push(
          <div key="pick" className="onb-pick">
            <span>{returning ? 'Продолжим' : 'Ваш первый урок'}</span>
            <strong>{returning ? 'Продолжим с того, что вы открывали' : pick.title}</strong>
            {!returning && <p>{reason(pick)}</p>}
          </div>);
        actions.push(button(state.editing ? 'Сохранить настройки' : returning ? 'Сохранить и продолжить →' : 'Открыть первый урок →',
          () => send('complete', {diagnostic_choice: 'skip'}, state.editing ? null : returning ? state.return_to : pick.url)));
      } else {
        body.push(<p key="none">Сейчас нет доступного стартового урока. Можно исследовать карту и вернуться позже.</p>);
        actions.push(button('Сохранить и открыть карту', () => send('complete', {}, '/')));
      }
      if (state.diagnostic.available) {
        body.push(<p key="diag">Уже знакомы с темой? Можно начать с необязательной проверки знаний.</p>);
        actions.push(button('Сначала проверить знания', () => send('complete', {diagnostic_choice: 'start'}, '/diagnostic'), 'secondary'));
      }
    }
    if (state.step !== 'start') actions.push(button(state.step === 'welcome' ? 'Найти своё начало →' : 'Сохранить и дальше →', () => send('next')));
    if (state.step !== 'welcome') actions.push(button('← Назад', () => send('back'), 'quiet'));
    actions.push(button(state.editing ? 'Отменить изменения' : 'Пропустить настройку', () => send(state.editing ? 'cancel' : 'skip'), 'quiet'));
  }

  return (
    <section className="onboarding" data-step={index < 0 ? 'done' : STEPS[index]}>
      <div className="onboarding-copy">
        <p className="eyebrow">AI Room · Ваше начало</p>
        <p id="onboarding-progress">{progress}</p>
        <div className="onb-steps" aria-hidden="true" hidden={index < 0}>
          {STEPS.map((step, i) => <span key={step} className={i <= index ? 'is-done' : undefined} />)}
        </div>
        <h1 id="onboarding-title" tabIndex={-1} ref={title}>{heading}</h1>
        <div id="onboarding-body">{body}</div>
        <div className="onboarding-footer" ref={footer}>
          <p id="onboarding-status" role="status" tabIndex={-1} ref={statusRef}>{status}</p>
          <div id="onboarding-actions" className="development-actions">{actions}</div>
        </div>
      </div>
      <aside className="onboarding-art" aria-hidden="true"><p>Пробуйте. Сохраняйте.<br />Возвращайтесь к своему.</p></aside>
    </section>
  );
}
