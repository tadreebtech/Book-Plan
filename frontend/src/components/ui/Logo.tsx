/**
 * Logo — brand mark + wordmark.
 * The SVG mark is the asset from `data_icon/01 · Зелёный/Сад/09/Знак/календарь.svg`.
 */

import logoMark from '../../assets/logo-mark.svg'
import './Logo.css'

/** Logo size: `md` in the header, `sm` in the footer. */
export type LogoSize = 'md' | 'sm'

export interface LogoProps {
  size?: LogoSize
}

export default function Logo({ size = 'md' }: LogoProps) {
  return (
    <a
      className={size === 'sm' ? 'logo logo--sm' : 'logo'}
      href="#top"
      aria-label="Book&Plan — на главную"
    >
      <img className="logo__mark" src={logoMark} alt="" width="30" height="34" />
      <span>Book&amp;Plan</span>
    </a>
  )
}
