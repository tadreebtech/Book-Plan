/**
 * EventsSection — "Для мероприятий" callout with the plan preview card.
 * Design: block 05 of the desktop layout.
 */

import { EVENT_PLAN } from '../../data/eventPlan'
import Lines from '../ui/Lines'
import './EventsSection.css'

export default function EventsSection() {
  return (
    <section className="section section--page" id="events">
      <div className="container">
        <div className="event">
          <div>
            <p className="eyebrow">{EVENT_PLAN.eyebrow}</p>
            <h3>
              <Lines lines={EVENT_PLAN.title} />
            </h3>
            <p>{EVENT_PLAN.text}</p>
          </div>

          <div className="plan">
            <p className="label">{EVENT_PLAN.planLabel}</p>
            <h4>{EVENT_PLAN.planTitle}</h4>
            <ul className="chips">
              {EVENT_PLAN.planItems.map((item) => (
                <li className="chip" key={item}>
                  {item}
                </li>
              ))}
            </ul>
            <p>{EVENT_PLAN.planNote}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
