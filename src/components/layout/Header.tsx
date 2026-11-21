/**
 * Header — sticky top bar: logo, main navigation, auth actions.
 * Navigation links come from `src/data/navigation.js` and point to section ids.
 */

import { NAV_LINKS } from '../../data/navigation'
import Button from '../ui/Button'
import Logo from '../ui/Logo'
import './Header.css'

export default function Header() {
  return (
    <header className="site-header">
      <div className="container site-header__inner">
        <Logo />

        <nav className="nav" aria-label="Основная навигация">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>

        <div className="header-actions">
          <Button href="#login" variant="ghost" size="sm">
            Войти
          </Button>
          <Button href="#register" variant="primary" size="sm">
            Зарегистрироваться
          </Button>
        </div>
      </div>
    </header>
  )
}
