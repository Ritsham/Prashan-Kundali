import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import PrashnaPage from './pages/PrashnaPage'
import PrashnaResultPage from './pages/PrashnaResultPage'
import BookingPage from './pages/BookingPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AstroCommunityPage from './pages/AstroCommunityPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="prashna" element={<PrashnaPage />} />
          <Route path="prashna-result" element={<PrashnaResultPage />} />
          <Route path="booking" element={<BookingPage />} />
          <Route path="astro-community" element={<AstroCommunityPage />} />
          <Route path="admin" element={<AdminDashboardPage />} />
          {/* Add more routes here as we migrate */}
          <Route path="*" element={<div className="p-8 text-center text-gray-500">Page not found or not yet migrated</div>} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
