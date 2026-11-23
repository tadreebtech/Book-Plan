/**
 * Demo bookings for the "Мои бронирования" card (hero preview + full section).
 *
 * This is static demo content — not a real user's bookings.
 * Later it will be replaced by data from the backend/database; the UI only
 * depends on the `Booking` type from `src/types`.
 */

import type { Booking } from '../types'

export const BOOKINGS: Booking[] = [
  {
    id: 'conference-hall',
    title: 'Конференц-зал',
    meta: '12 ноября · 10:00–13:00',
    status: 'Подтверждено',
    tone: 'ok',
  },
  {
    id: 'photographer',
    title: 'Фотограф',
    meta: '15 ноября · съёмка 2 часа',
    status: 'Ожидает ответа',
    tone: 'wait',
  },
  {
    id: 'restaurant-table',
    title: 'Столик в ресторане',
    meta: '20 ноября · 19:00 · 4 гостя',
    status: 'Запрос отправлен',
    tone: 'sent',
  },
]

/** Small caption under the hero preview card. */
export const BOOKINGS_PREVIEW_NOTE = 'Ресурс, дата и статус — в карточке бронирования'
