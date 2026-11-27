/**
 * Header — sticky top bar: logo, main navigation, auth actions.
 * Navigation links come from `src/data/navigation` and point to section ids.
 * On mobile (≤ 1024px) the nav and auth buttons are hidden behind a
 * "Меню" toggle button that slides a panel down when opened.
 */

import { useState } from 'react'
import { NAV_LINKS } from '../../data/navigation'
import Button from '../ui/Button'
import Logo from '../ui/Logo'
import './Header.css'

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="site-header">
      <div className="container site-header__inner">
        <Logo />

        <nav className="nav" aria-label="Основная навигация">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} onClick={() => setIsMenuOpen(false)}>
              {link.label}
            </a>
          ))}
        </nav>

        <div className="header-actions">
          {/* Authentication is not implemented yet — disabled placeholders.
              Hidden on mobile by Header.css; the menu panel has its own copy. */}
          <Button variant="ghost" size="sm" disabled title="Раздел в разработке">
            Войти
          </Button>
          <Button variant="primary" size="sm" disabled title="Раздел в разработке">
            Зарегистрироваться
          </Button>

          <button
            type="button"
            className={`menu-toggle ${isMenuOpen ? 'menu-toggle--open' : ''}`}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-menu"
            onClick={() => setIsMenuOpen((prev) => !prev)}
          >
            Меню
          </button>

          {isMenuOpen && (
            <div className="mobile-menu" id="mobile-menu">
              <nav className="mobile-nav" aria-label="Навигация (мобильное меню)">
                {NAV_LINKS.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    className="mobile-nav__link"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {link.label}
                  </a>
                ))}
              </nav>

              <div className="mobile-actions">
                {/* Authentication is not implemented yet — disabled placeholders. */}
                <Button variant="ghost" size="sm" disabled title="Раздел в разработке">
                  Войти
                </Button>
                <Button variant="primary" size="sm" disabled title="Раздел в разработке">
                  Зарегистрироваться
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
