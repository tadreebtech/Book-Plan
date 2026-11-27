/**
 * FAQSection — accordion-style "Частые вопросы" block.
 *
 * Layout matches the design exactly:
 * - Left column: eyebrow + heading + supporting text.
 * - Right column: accordion cards (one open at a time).
 *
 * Design tokens (colors, fonts, spacing) come from src/styles/tokens.css
 * and src/styles/base.css, matching the rest of the landing page.
 */

import { useState } from 'react'
import { FAQS } from '../../data/faqs'
import type { FAQItem } from '../../data/faqs'
import './FAQSection.css'

export interface FAQSectionProps {
  /** Optional custom list of FAQ items. Defaults to src/data/faqs. */
  items?: FAQItem[]
}

export default function FAQSection({ items = FAQS }: FAQSectionProps) {
  const [activeId, setActiveId] = useState<string | null>(null)

  const isOpen = (id: string) => activeId === id

  const toggle = (id: string) => {
    setActiveId((current) => (current === id ? null : id))
  }

  return (
    <section className="section section--page" id="faq">
      <div className="container">
        <div className="faq__header">
          <div className="faq__head">
            <p className="eyebrow">ВОПРОСЫ И ОТВЕТЫ</p>
            <h2>Частые вопросы</h2>
            <p className="faq__lead">О пользе ресурсов, бронирований и работе с платформой.</p>
          </div>

          <div className="faqs">
            {items.map((faq) => {
              const open = isOpen(faq.id)
              return (
                <article key={faq.id} className={`faq faq--${open ? 'open' : 'closed'}`}>
                  <button
                    type="button"
                    className="faq__trigger"
                    onClick={() => toggle(faq.id)}
                    aria-expanded={open}
                    aria-controls={`faq-answer-${faq.id}`}
                  >
                    <span className="faq__question">{faq.question}</span>
                    <span className="faq__icon">{open ? '−' : '+'}</span>
                  </button>
                  {open && (
                    <div className="faq__answer" id={`faq-answer-${faq.id}`} role="region">
                      {faq.answer}
                    </div>
                  )}
                </article>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
