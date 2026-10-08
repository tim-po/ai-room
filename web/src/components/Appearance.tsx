import {useState} from 'react';

// Настройки → Оформление: the palette («Закат» or the club's own «AI Room») and day or night.
// club/static/theme.js applies and remembers both on this device.

type Palette = 'sunset' | 'club';
type Mode = 'auto' | 'dawn' | 'dusk';
declare global {
  interface Window {
    AIRoomTheme?: {setPalette: (p: Palette) => void; setMode: (m: Mode) => void; palette: () => Palette; mode: () => string};
  }
}

const PALETTES: {id: Palette; title: string; note: string; swatches: string[]}[] = [
  {id: 'club', title: 'AI Room', note: 'Фирменные цвета клуба: лайм, белый и графит', swatches: ['#1a1a18', '#dfff4f', '#f4f6f6', '#31b545']},
  {id: 'sunset', title: 'Закат', note: 'Тёплое небо, рассвет и сумерки', swatches: ['#2b1a12', '#ff9f34', '#fff6ec', '#cf5a7e']},
];
const MODES: [Mode, string][] = [['auto', 'Как в системе'], ['dawn', 'День'], ['dusk', 'Ночь']];

export default function Appearance() {
  const theme = typeof window !== 'undefined' ? window.AIRoomTheme : undefined;
  const [palette, setPalette] = useState<Palette>(theme?.palette() ?? 'sunset');
  const [mode, setMode] = useState<Mode>((theme?.mode() as Mode) ?? 'auto');
  return (
    <section className="settings-form appearance" aria-labelledby="appearance-title">
      <h2 id="appearance-title">Оформление</h2>
      <div className="appearance-palettes" role="radiogroup" aria-label="Тема">
        {PALETTES.map(p => (
          <button key={p.id} type="button" role="radio" aria-checked={palette === p.id} className={'appearance-palette' + (palette === p.id ? ' is-on' : '')}
            onClick={() => { setPalette(p.id); theme?.setPalette(p.id); }}>
            <span className="appearance-swatches" aria-hidden="true">{p.swatches.map(c => <i key={c} style={{background: c}} />)}</span>
            <strong>{p.title}</strong>
            <small>{p.note}</small>
          </button>
        ))}
      </div>
      <div className="appearance-modes" role="radiogroup" aria-label="Время суток">
        {MODES.map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={mode === id} className={mode === id ? 'is-on' : undefined}
            onClick={() => { setMode(id); theme?.setMode(id); }}>{label}</button>
        ))}
      </div>
      <p className="small">День и ночь также переключаются кнопкой с солнцем в шапке. Выбор хранится на этом устройстве.</p>
    </section>
  );
}
