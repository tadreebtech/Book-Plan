/**
 * Domain types shared by data modules and components.
 *
 * Keeping the content shapes here makes it obvious what the UI expects and
 * what a future backend/database has to return.
 */

/** Visual tone of a booking status pill. */
export type BookingTone = 'ok' | 'wait' | 'sent'

/** A booking request shown in the "Мои бронирования" card. */
export interface Booking {
  id: string
  title: string
  meta: string
  status: string
  tone: BookingTone
}

/** A navigation link; `href` points to an in-page anchor (`#section-id`). */
export interface NavLink {
  label: string
  href: string
}

/** Secondary category card (services / venues). */
export interface Category {
  id: string
  label: string
  title: string
  text: string
}

/** Featured category card; its copy is split into design lines. */
export interface FeaturedCategory {
  label: string
  title: string[]
  text: string[]
}

/** One step of the "Как забронировать" flow. */
export interface BookingStep {
  id: string
  label: string
  title: string
  text: string
}

/** One row of the "Поставщикам" list. */
export interface ProviderStep {
  id: string
  num: string
  title: string
  text: string
}

/** "Для мероприятий" callout and its plan preview card. */
export interface EventPlan {
  eyebrow: string
  title: string[]
  text: string
  planLabel: string
  planTitle: string
  planItems: string[]
  planNote: string
}
