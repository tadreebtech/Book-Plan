/**
 * "Категории" section content.
 *
 * The featured card is intentionally larger than the other two, so it has its
 * own type. `title` / `text` are arrays of lines — each entry is rendered on
 * a separate line (line breaks are part of the design).
 */

import type { Category, FeaturedCategory } from '../types'

export const FEATURED_CATEGORY: FeaturedCategory = {
  label: '01 / Университет',
  title: ['Аудитории и специальные', 'помещения'],
  text: ['Лекционные залы, лаборатории', 'и конференц-залы'],
}

export const CATEGORIES: Category[] = [
  {
    id: 'services',
    label: '02 / Услуги',
    title: 'Специалисты и оборудование',
    text: 'Фотографы, кейтеринг, музыканты и аренда',
  },
  {
    id: 'venues',
    label: '03 / Заведения',
    title: 'Места для встреч и отдыха',
    text: 'Кафе, рестораны, бары и банкетные залы',
  },
]
