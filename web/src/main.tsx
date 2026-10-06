import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {createBrowserRouter, isRouteErrorResponse, RouterProvider, useRouteError} from 'react-router';
import {ApiError} from './api';
import './app.css';
import Home, {homeLoader} from './pages/Home';
import LessonPage, {lessonLoader} from './pages/Lesson';
import Profile, {profileLoader} from './pages/Profile';
import Shell, {AppLink} from './Shell';

function RouteError() {
  const error = useRouteError();
  const status = error instanceof ApiError ? error.status : isRouteErrorResponse(error) ? error.status : 0;
  const notFound = status === 404;
  return (
    <section className="error-page">
      <p className="eyebrow">{status || 'Ошибка'}</p>
      <h1>{notFound ? 'Такой страницы нет' : 'Не удалось открыть страницу'}</h1>
      <p className="lead">{notFound ? 'Возможно, урок перенесли или ссылка устарела.' : error instanceof ApiError ? error.message : 'Проверьте подключение и обновите страницу.'}</p>
      <div className="actions">
        <AppLink className="button" to="/">На карту навыков</AppLink>
        {!notFound && <button type="button" className="button secondary" onClick={() => window.location.reload()}>Обновить</button>}
      </div>
    </section>
  );
}

const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [{
      errorElement: <RouteError />,
      children: [
        {path: '/', element: <Home />, loader: homeLoader},
        {path: '/lessons/:id', element: <LessonPage />, loader: lessonLoader},
        {path: '/profile', element: <Profile />, loader: profileLoader},
      ],
    }],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
