/**
 * BookingsSection — full "Ваши бронирования" section.
 * Reuses `BookingsCard` in its wide variant; no section-specific styles.
 */

import BookingsCard from '../bookings/BookingsCard'
import SectionHeader from '../ui/SectionHeader'

export default function BookingsSection() {
  return (
    <section className="section section--white" id="bookings">
      <div className="container">
        <SectionHeader
          eyebrow="После отправки запроса"
          title={
            <>
              Ваши бронирования:
              <br />
              даты, детали и статусы
            </>
          }
          lead="Проверяйте, что вы выбрали, на какое время отправили запрос и получили ли ответ поставщика."
        />

        <BookingsCard variant="wide" />
      </div>
    </section>
  )
}
