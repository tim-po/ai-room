import {useState, type FormEvent} from 'react';
import {useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {ApiError, getJson, postJson} from '../api';
import Appearance from '../components/Appearance';
import PlanEditor from '../components/PlanEditor';
import Select from '../components/Select';
import {AppLink} from '../Shell';
import type {PreferencesData} from '../types';
import {useTitle} from '../useTitle';

export const preferencesLoader = ({request}: LoaderFunctionArgs) => getJson<PreferencesData>('/api/app/preferences', request.signal);

const EXPERIENCE = [['beginner', 'Начинаю разбираться'], ['experienced', 'Уже использую в работе']] as const;

export default function Preferences() {
  const data = useLoaderData() as PreferencesData;
  const navigate = useNavigate();
  useTitle('Настройки');
  const [experience, setExperience] = useState<string>(data.experience);
  // The plan below owns the weekly goal (one session per chosen day); this form only resends it.
  const [weekly, setWeekly] = useState(data.weekly_goal);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      await postJson('/preferences', {goal: data.goal, experience, weekly_goal: String(weekly)});
      navigate('/profile', {state: {notice: 'Настройки сохранены.'}});
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
      setBusy(false);
    }
  }
  return (
    <section className="settings">
      <h1>Настройки</h1>
      <p className="lead">Оформление, план и опыт. Пропущенная неделя ничего не обнуляет.</p>
      <Appearance />
      <section className="settings-form settings-plan" id="plan" aria-labelledby="plan-title">
        <h2 id="plan-title">План занятий</h2>
        <p className="small">Выберите дни и время — добавим занятия в ваш календарь со ссылкой, которая откроет урок там, где вы остановились.</p>
        <PlanEditor initial={data.plan} onSaved={plan => setWeekly(plan.days.length)} />
      </section>
      <form className="settings-form" onSubmit={submit}>
        <Select label="Опыт с ИИ" value={experience} onChange={setExperience} options={EXPERIENCE} />
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
