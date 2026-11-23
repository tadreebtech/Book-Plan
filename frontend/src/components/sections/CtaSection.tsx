/**
 * CtaSection — final dark call-to-action block.
 * Design: block 07 of the desktop layout (before the footer).
 */

import Button from '../ui/Button'
import './CtaSection.css'

export default function CtaSection() {
  return (
    <section className="section section--white section--cta">
      <div className="container">
        <div className="cta">
          <h2>
            Начните с нужного
            <br />
            бронирования
          </h2>

          <div>
            <p>Зарегистрируйтесь, чтобы отправлять запросы и следить за ответами поставщиков.</p>
            <div className="cta__actions">
              {/* Authentication is not implemented yet — disabled placeholders. */}
              <Button variant="light" disabled title="Раздел в разработке">
                Зарегистрироваться
              </Button>
              <button type="button" className="cta__link" disabled title="Раздел в разработке">
                Уже есть аккаунт? Войти
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
