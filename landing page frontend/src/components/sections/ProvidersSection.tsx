/**
 * ProvidersSection — "Поставщикам" numbered rows.
 * Desktop layout is a 3-column row: number | title | description.
 */

import { PROVIDER_STEPS } from '../../data/providers'
import SectionHeader from '../ui/SectionHeader'
import './ProvidersSection.css'

export default function ProvidersSection() {
  return (
    <section className="section section--white" id="providers">
      <div className="container">
        <SectionHeader
          eyebrow="Поставщикам"
          title={
            <>
              Предлагайте ресурсы.
              <br />
              Управляйте запросами.
            </>
          }
          lead="Размещайте предложения, отмечайте доступные даты и отвечайте на запросы клиентов."
        />

        <div className="providers">
          {PROVIDER_STEPS.map((item) => (
            <article className="provider" key={item.id}>
              <p className="num">{item.num}</p>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
