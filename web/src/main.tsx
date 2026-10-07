import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {createBrowserRouter, RouterProvider} from 'react-router';
import './app.css';
import './loop.css';
import {NotFound, RouteError} from './ErrorPage';
import Catalogue, {catalogueLoader} from './pages/Catalogue';
import Consent, {consentLoader} from './pages/Consent';
import Course, {courseLoader} from './pages/Course';
import Help, {helpLoader} from './pages/Help';
import Home, {homeLoader} from './pages/Home';
import LessonPage, {lessonLoader} from './pages/Lesson';
import Login from './pages/Login';
import Material, {materialLoader} from './pages/Material';
import Membership, {membershipLoader} from './pages/Membership';
import Onboarding, {onboardingLoader, onboardingShouldRevalidate} from './pages/Onboarding';
import Preferences, {preferencesLoader} from './pages/Preferences';
import Profile, {profileLoader} from './pages/Profile';
import Shell, {ShellFallback} from './Shell';

const router = createBrowserRouter([
  {
    element: <Shell />,
    hydrateFallbackElement: <ShellFallback />,
    children: [{
      errorElement: <RouteError />,
      children: [
        {path: '/', element: <Home />, loader: homeLoader},
        {path: '/catalogue', element: <Catalogue />, loader: catalogueLoader},
        {path: '/courses/:id', element: <Course />, loader: courseLoader},
        {path: '/lessons/:id', element: <LessonPage />, loader: lessonLoader},
        {path: '/materials/:id', element: <Material />, loader: materialLoader},
        {path: '/profile', element: <Profile />, loader: profileLoader},
        {path: '/preferences', element: <Preferences />, loader: preferencesLoader},
        {path: '/membership', element: <Membership />, loader: membershipLoader},
        {path: '/help', element: <Help />, loader: helpLoader},
        {path: '/onboarding', element: <Onboarding />, loader: onboardingLoader, shouldRevalidate: onboardingShouldRevalidate},
        {path: '/login', element: <Login />},
        {path: '/oauth/consent', element: <Consent />, loader: consentLoader},
        {path: '*', element: <NotFound />},
      ],
    }],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
