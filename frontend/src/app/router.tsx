import { createBrowserRouter } from 'react-router-dom';

import { AppShell } from '../components/AppShell';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SetupStatusPage } from '../pages/SetupStatusPage';
import { LoginPage } from '../pages/LoginPage';
import { IncidentsPage } from '../pages/IncidentsPage';
import { IncidentDetailPage } from '../pages/IncidentDetailPage';
import { ReliabilityPage } from '../pages/ReliabilityPage';
import { SystemStatusPage } from '../pages/SystemStatusPage';
import { DashboardPage } from '../pages/DashboardPage';
import { EvaluationsPage } from '../pages/EvaluationsPage';
import { PublicContextPage } from '../pages/PublicContextPage';
import { SourceContextPage } from '../pages/SourceContextPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <SetupStatusPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'incidents', element: <IncidentsPage /> },
      { path: 'incidents/:incidentId', element: <IncidentDetailPage /> },
      { path: 'reliability', element: <ReliabilityPage /> },
      { path: 'evaluations', element: <EvaluationsPage /> },
      { path: 'public-context', element: <PublicContextPage /> },
      { path: 'sources/:sourceId/context', element: <SourceContextPage /> },
      { path: 'system', element: <SystemStatusPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
