import {useState, type FormEvent} from 'react';
import {useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {ApiError, getJson, postJson} from '../api';
import Select from '../components/Select';
import {AppLink} from '../Shell';
import type {PreferencesData} from '../types';
import {useTitle} from '../useTitle';

export const preferencesLoader = ({request}: LoaderFunctionArgs) => getJson<PreferencesData>('/api/app/preferences', request.signal);

const EXPERIENCE = [['beginner', 'Начинаю разбираться'], ['experienced', 'Уже использую в работе']] as const;
const WEEKLY = [['0', 'Без цели — учусь, когда удобно'], ['1', '1 урок в неделю'], ['2', '2 урока в неделю'], ['3', '3 урока в неделю'], ['5', '5 уроков в неделю']] as const;

export default function Preferences() {
  const data = useLoaderData() as PreferencesData;
  const navigate = useNavigate();
  useTitle('Настройки обучения');
  const [experience, setExperience] = useState<string>(data.experience);
  const [weekly, setWeekly] = useState(String(data.weekly_goal));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      await postJson('/preferences', {goal: data.goal, experience, weekly_goal: weekly});
      navigate('/profile', {state: {notice: 'Настройки сохранены.'}});
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
      setBusy(false);
    }
  }
  return (
    <section className="settings">
      <p className="eyebrow">Моё обучение</p>
      <h1>Настройки обучения</h1>
      <p className="lead">Темп и опыт помогают подобрать уроки. Пропущенная неделя ничего не обнуляет.</p>
      <form className="settings-form" onSubmit={submit}>
        <Select label="Опыт с ИИ" value={experience} onChange={setExperience} options={EXPERIENCE} />
        <Select label="Недельная цель" value={weekly} onChange={setWeekly} options={WEEKLY} />
        {error && <p className="notice error" role="alert">{error}</p>}
        <div className="actions">
          <button className="button" disabled={busy}>Сохранить</button>
          <AppLink className="button secondary" to="/profile">Отмена</AppLink>
        </div>
      </form>
      <div className="settings-more">
        <h2>Интересы</h2>
        <p>Направления, с которых удобно начинать. Вся карта всё равно открыта.</p>
        <AppLink to="/onboarding">Изменить интересы →</AppLink>
      </div>
    </section>
  );
}
