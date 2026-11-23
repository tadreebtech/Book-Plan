/**
 * Footer — brand, short navigation and a tagline.
 */

import { FOOTER_LINKS } from '../../data/navigation'
import Logo from '../ui/Logo'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__inner">
        <Logo size="sm" />

        <nav className="footer-nav" aria-label="Навигация в подвале">
          {FOOTER_LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>

        <p className="footer-note">Бронирование и планирование</p>
      </div>
    </footer>
  )
}
