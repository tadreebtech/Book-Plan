/**
 * BookingsCard — "Мои бронирования" preview card.
 *
 * Used twice:
 *  - default variant → hero preview (`HeroSection`)
 *  - `variant="wide"` → full section (`BookingsSection`)
 *
 * Data comes from `src/data/bookings.js` (demo content for now).
 */

import { BOOKINGS } from '../../data/bookings'
import type { Booking } from '../../types'
import StatusPill from '../ui/StatusPill'
import './BookingsCard.css'

/** `default` = hero preview card, `wide` = full "Мои бронирования" section. */
export type BookingsCardVariant = 'default' | 'wide'

export interface BookingsCardProps {
  variant?: BookingsCardVariant
  /** Bookings to render; defaults to the demo data from `src/data/bookings`. */
  items?: Booking[]
}

export default function BookingsCard({ variant = 'default', items = BOOKINGS }: BookingsCardProps) {
  const isWide = variant === 'wide'

  return (
    <article className={isWide ? 'bcard bcard--wide' : 'bcard'}>
      <div className="bcard__head">
        <h3 className="bcard__title">Мои бронирования</h3>
        <p className="bcard__sub">Пример интерфейса · демонстрационные данные</p>

        {/* Tabs are visual only: filtering is not implemented yet. */}
        <div className="bcard__tabs" role="tablist" aria-label="Фильтр бронирований">
          <button type="button" className="tab tab--active" role="tab" aria-selected="true">
            Все запросы
          </button>
          <button type="button" className="tab" role="tab" aria-selected="false">
            Ближайшие
          </button>
        </div>
      </div>

      <ul className="bcard__rows">
        {items.map((booking) => (
          <li className="brow" key={booking.id}>
            <div>
              <p className="brow__title">{booking.title}</p>
              <p className="brow__meta">{booking.meta}</p>
            </div>
            <StatusPill tone={booking.tone}>{booking.status}</StatusPill>
          </li>
        ))}
      </ul>
    </article>
  )
}
