/**
 * HeroSection — first screen.
 *
 * Contents: eyebrow, h1, lead, two CTAs, note and the "Мои бронирования"
 * preview card inside a soft green panel.
 * Design: `book & plan/01 · Зелёный/Сад/Desktop 1440.png` — block 01.
 */

import { BOOKINGS_PREVIEW_NOTE } from '../../data/bookings'
import BookingsCard from '../bookings/BookingsCard'
import Button from '../ui/Button'
import './HeroSection.css'

export default function HeroSection() {
  return (
    <section className="hero">
      <div className="container hero__inner">
        <div className="hero__content">
          <p className="eyebrow">Единая платформа бронирования</p>

          <h1>
            Бронируйте
            <br />
            помещения, услуги
            <br />и заведения
          </h1>

          <p className="hero__lead">
            Находите подходящие варианты и отправляйте запросы на выбранные даты. Для мероприятия
            объединяйте несколько бронирований в отдельный план.
          </p>

          <div className="hero__actions">
            <Button href="#register">Зарегистрироваться</Button>
            <Button href="#login" variant="ghost">
              Войти
            </Button>
          </div>

          <p className="hero__note">Запрос на бронирование подтверждает поставщик.</p>
        </div>

        <div className="hero__panel">
          <BookingsCard />
          <p className="panel-note">{BOOKINGS_PREVIEW_NOTE}</p>
        </div>
      </div>
    </section>
  )
}
