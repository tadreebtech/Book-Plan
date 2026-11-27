/**
 * StatusPill — booking status badge.
 * `tone` maps to a color pair: ok (green) | wait (amber) | sent (grey).
 */

import type { ReactNode } from 'react'
import type { BookingTone } from '../../types'
import './StatusPill.css'

export interface StatusPillProps {
  /** Status color: ok (подтверждено) | wait (ожидает) | sent (запрос отправлен). */
  tone?: BookingTone
  children: ReactNode
}

export default function StatusPill({ tone = 'sent', children }: StatusPillProps) {
  return <span className={`pill pill--${tone}`}>{children}</span>
}
