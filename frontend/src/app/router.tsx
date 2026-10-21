import { createBrowserRouter } from 'react-router-dom';

import { AppShell } from '../components/AppShell';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SublevelStudioLandingPage } from '../pages/SublevelStudioLandingPage';

export const router = createBrowserRouter([
  { path: '/', element: <SublevelStudioLandingPage /> },
  {
    path: '*',
    element: <AppShell />,
    children: [{ index: true, element: <NotFoundPage /> }],
  },
]);
