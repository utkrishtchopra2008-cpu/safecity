import { createBrowserRouter } from 'react-router-dom';

import { AppShell } from '../components/AppShell';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SetupStatusPage } from '../pages/SetupStatusPage';

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <SetupStatusPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
