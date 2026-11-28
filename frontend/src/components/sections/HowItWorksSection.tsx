/**
 * HowItWorksSection — three-step booking flow.
 * Numbered steps are rendered as an ordered list (`<ol>`) for semantics,
 * while the visual numbering comes from the "Шаг 01/02/03" labels.
 */

import { BOOKING_STEPS } from '../../data/steps'
import SectionHeader from '../ui/SectionHeader'
import './HowItWorksSection.css'

export default function HowItWorksSection() {
  return (
    <section className="section section--page" id="how">
      <div className="container">
        <SectionHeader
          eyebrow="Как забронировать"
          title={
            <>
              От поиска —<br />к ответу поставщика
            </>
          }
          lead="Для отдельного бронирования не нужно создавать мероприятие."
        />

        <ol className="steps">
          {BOOKING_STEPS.map((step) => (
            <li className="step" key={step.id}>
              <p className="label">{step.label}</p>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
