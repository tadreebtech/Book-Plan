/**
 * "Для мероприятий" block + the "Пример плана" preview card.
 * `title` is an array of lines (explicit line breaks, as in the design).
 */

import type { EventPlan } from '../types'

export const EVENT_PLAN: EventPlan = {
  eyebrow: 'Для мероприятий',
  title: ['Несколько бронирований', 'для одного события?'],
  text: 'Объединяйте подтверждённые бронирования площадки, услуг и оборудования в отдельный план.',
  planLabel: 'Пример плана',
  planTitle: 'Конференция',
  planItems: ['Конференц-зал', 'Фотограф', 'Оборудование'],
  planNote: 'Для отдельного бронирования план не нужен.',
}
