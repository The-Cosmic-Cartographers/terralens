import { lazy } from 'react'

// Each page is loaded on demand: the overview pulls in MapLibre, the detail
// view pulls in Recharts, and neither weighs down the first paint.
export const HomePage = lazy(() => import('./HomePage.jsx'))
export const ExplorePage = lazy(() => import('./ExplorePage.jsx'))
export const VariableDetailPage = lazy(() => import('./VariableDetailPage.jsx'))
export const ComparePage = lazy(() => import('./ComparePage.jsx'))
export const CaseFilesPage = lazy(() => import('./CaseFilesPage.jsx'))
