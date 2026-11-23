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
          <p className="eyebrow">
            <span className="desktop-only">Единая платформа бронирования</span>
            <span className="mobile-only">Платформа бронирования</span>
          </p>

          <h1>
            Бронируйте
            <br />
            помещения, услуги
            <br />и заведения
          </h1>

          <p className="hero__lead">
            <span className="desktop-only">
              Находите подходящие варианты и отправляйте запросы на выбранные даты. Для мероприятия
              объединяйте несколько бронирований в отдельный план.
            </span>
            <span className="mobile-only">
              Выбирайте ресурс и отправляйте запрос на нужную дату. Для мероприятия можно собрать
              отдельный план.
            </span>
          </p>

          <div className="hero__actions">
            {/* Authentication is not implemented yet — disabled placeholders. */}
            <Button disabled title="Раздел в разработке">
              Зарегистрироваться
            </Button>
            <Button variant="ghost" disabled title="Раздел в разработке">
              Войти
            </Button>
          </div>

          <p className="hero__note">
            <span className="desktop-only">Запрос на бронирование подтверждает поставщик.</span>
            <span className="mobile-only">Бронирование подтверждает поставщик.</span>
          </p>
        </div>

        <div className="hero__panel">
          <BookingsCard />
          <p className="panel-note">{BOOKINGS_PREVIEW_NOTE}</p>
        </div>
      </div>
    </section>
  )
}
