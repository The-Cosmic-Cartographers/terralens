import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import App from './App.jsx'
import WindowProvider from './state/WindowProvider.jsx'
import {
  CaseFilesPage,
  ComparePage,
  ExplorePage,
  HomePage,
  SummaryPage,
  VariableDetailPage,
} from './pages'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <WindowProvider>
        <Routes>
          <Route element={<App />}>
            <Route index element={<HomePage />} />
            <Route path="summary" element={<SummaryPage />} />
            <Route path="explore" element={<ExplorePage />} />
            <Route
              path="explore/:variableId"
              element={<VariableDetailPage />}
            />
            <Route path="compare" element={<ComparePage />} />
            <Route path="case-files" element={<CaseFilesPage />} />
          </Route>
        </Routes>
      </WindowProvider>
    </BrowserRouter>
  </StrictMode>,
)
