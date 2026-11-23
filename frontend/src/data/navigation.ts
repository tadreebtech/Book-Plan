/**
 * Site navigation.
 * `href` values point to the section ids defined in `src/pages/HomePage.tsx`.
 */

import type { NavLink } from '../types'

export const NAV_LINKS: NavLink[] = [
  { label: 'Категории', href: '#categories' },
  { label: 'Как забронировать', href: '#how' },
  { label: 'Возможности', href: '#bookings' },
  { label: 'Поставщикам', href: '#providers' },
]

/** Footer uses a shorter version of the same navigation. */
export const FOOTER_LINKS: NavLink[] = [
  { label: 'Категории', href: '#categories' },
  { label: 'Как забронировать', href: '#how' },
  { label: 'Поставщикам', href: '#providers' },
]
