/**
 * "Поставщикам" section — three numbered rows for providers.
 */

import type { ProviderStep } from '../types'

export const PROVIDER_STEPS: ProviderStep[] = [
  {
    id: 'profile',
    num: '01',
    title: 'Профиль и объявления',
    text: 'Расскажите об услуге или помещении.',
  },
  {
    id: 'dates',
    num: '02',
    title: 'Доступные даты',
    text: 'Укажите, когда ресурс можно забронировать.',
  },
  {
    id: 'requests',
    num: '03',
    title: 'Обработка запросов',
    text: 'Рассмотрите запрос и сообщите решение клиенту.',
  },
]
