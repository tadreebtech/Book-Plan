// @vitest-environment happy-dom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import type { Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import App from '../App'
import FAQSection from '../components/sections/FAQSection'
import { FAQS } from '../data/faqs'

describe('FAQ: TG-142 / TG-143', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
    container = document.createElement('div')
    document.body.append(container)
    root = createRoot(container)
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
  })

  it.each(FAQS)('opens and closes the answer to "$question"', async (item) => {
    await act(async () => root.render(<FAQSection />))
    const buttons = [...container.querySelectorAll<HTMLButtonElement>('#faq button')]
    const trigger = buttons.find((button) => button.textContent?.includes(item.question))!
    expect(trigger).toBeDefined()
    expect(trigger.disabled).toBe(false)

    await act(async () => trigger.click())

    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    const answerId = trigger.getAttribute('aria-controls')
    expect(answerId).toBeTruthy()
    const answer = document.getElementById(answerId!)
    expect(answer).not.toBeNull()
    expect(answer!.textContent?.trim()).toBe(item.answer)
    expect(answer!.getAttribute('role')).toBe('region')

    await act(async () => trigger.click())

    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(document.getElementById(answerId!)).toBeNull()
  })

  it('replaces the previous answer when another question is opened', async () => {
    await act(async () => root.render(<FAQSection />))
    const buttons = [...container.querySelectorAll<HTMLButtonElement>('#faq button')]
    await act(async () => buttons[0].click())
    await act(async () => buttons[1].click())

    expect(buttons[0].getAttribute('aria-expanded')).toBe('false')
    expect(buttons[1].getAttribute('aria-expanded')).toBe('true')
    const answers = container.querySelectorAll('[role="region"]')
    expect(answers).toHaveLength(1)
    expect(answers[0].textContent).toBe(FAQS[1].answer)
  })

  it('places the complete FAQ after the final CTA and before the footer', async () => {
    await act(async () => root.render(<App />))
    const faq = container.querySelector('#faq')!
    const cta = container.querySelector('.section--cta')!
    const footer = container.querySelector('footer')!
    expect(faq).not.toBeNull()
    expect(cta).not.toBeNull()
    expect(footer).not.toBeNull()
    expect(cta.compareDocumentPosition(faq) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(faq.compareDocumentPosition(footer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(faq.querySelectorAll('button')).toHaveLength(12)
    expect(faq.querySelector('h2')?.textContent).toBe('Частые вопросы')
  })
})
