/**
 * App — application shell.
 *
 * Holds the layout chrome shared by every page (header, footer, page wrapper).
 * Page content lives in `src/pages/`; sections live in `src/components/sections/`.
 *
 * When routing is added, render the router here instead of `<HomePage />`.
 */

import Footer from './components/layout/Footer'
import Header from './components/layout/Header'
import HomePage from './pages/HomePage'

export default function App() {
  return (
    <div className="page" id="top">
      <Header />

      <main>
        <HomePage />
      </main>

      <Footer />
    </div>
  )
}
