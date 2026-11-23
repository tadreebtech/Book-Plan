/**
 * "Как забронировать" — three-step flow.
 * Keep the copy short: the layout is a 3-column grid on desktop.
 */

import type { BookingStep } from '../types'

export const BOOKING_STEPS: BookingStep[] = [
  {
    id: 'find',
    label: 'Шаг 01',
    title: 'Найдите ресурс',
    text: 'Выберите категорию и предложение, которое подходит под вашу задачу.',
  },
  {
    id: 'request',
    label: 'Шаг 02',
    title: 'Отправьте запрос',
    text: 'Укажите нужные даты, время и необходимые детали.',
  },
  {
    id: 'answer',
    label: 'Шаг 03',
    title: 'Получите ответ',
    text: 'Проверьте, подтвердил ли поставщик ваш запрос.',
  },
]
