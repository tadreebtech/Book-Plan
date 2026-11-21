/**
 * HomePage — landing page content.
 *
 * The sections below are rendered top → bottom in the same order as the design.
 * Every section lives in `src/components/sections/` and owns its own styles.
 * Layout chrome (header/footer) is handled by `App.jsx`, not here.
 *
 * Section ids are used by the navigation links (`src/data/navigation.js`).
 */

import BookingsSection from '../components/sections/BookingsSection'
import CategoriesSection from '../components/sections/CategoriesSection'
import CtaSection from '../components/sections/CtaSection'
import EventsSection from '../components/sections/EventsSection'
import HeroSection from '../components/sections/HeroSection'
import HowItWorksSection from '../components/sections/HowItWorksSection'
import ProvidersSection from '../components/sections/ProvidersSection'

export default function HomePage() {
  return (
    <>
      <HeroSection /> {/* 01 · first screen: headline + preview card */}
      <CategoriesSection /> {/* 02 · categories: university / services / venues */}
      <HowItWorksSection /> {/* 03 · how booking works: 3 steps */}
      <BookingsSection /> {/* 04 · full "Мои бронирования" card */}
      <EventsSection /> {/* 05 · event plan callout */}
      <ProvidersSection /> {/* 06 · for providers: 3 steps */}
      <CtaSection /> {/* 07 · final call to action */}
    </>
  )
}
