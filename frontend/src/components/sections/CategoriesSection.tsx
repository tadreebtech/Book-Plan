/**
 * CategoriesSection — one catalog, three resource types.
 * Featured card (university) + two secondary cards (services, venues).
 * Design: block 02 of the desktop layout.
 */

import { CATEGORIES, FEATURED_CATEGORY } from '../../data/categories'
import Lines from '../ui/Lines'
import SectionHeader from '../ui/SectionHeader'
import './CategoriesSection.css'

export default function CategoriesSection() {
  return (
    <section className="section section--white" id="categories">
      <div className="container">
        <SectionHeader
          eyebrow="Категории"
          title={
            <>
              Один каталог —<br />
              разные задачи
            </>
          }
          lead="Выберите помещение, специалиста или заведение. Оборудование в аренду ищите в разделе услуг."
        />

        <div className="categories">
          <article className="category-main">
            <p className="label">{FEATURED_CATEGORY.label}</p>
            <h3>
              <Lines lines={FEATURED_CATEGORY.title} />
            </h3>
            <p>
              <Lines lines={FEATURED_CATEGORY.text} />
            </p>
          </article>

          <div className="categories__side">
            {CATEGORIES.map((category) => (
              <article className="category" key={category.id}>
                <p className="label">{category.label}</p>
                <h3>{category.title}</h3>
                <p>{category.text}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
