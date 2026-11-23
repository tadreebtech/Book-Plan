/**
 * Bookings data tests.
 *
 * Validates that the static BOOKINGS data conforms to the
 * `Booking` type imported from `src/types`, ensuring that
 * future changes don't silently miss required fields.
 */

import { describe, it, expect } from 'vitest'
import { BOOKINGS, BOOKINGS_PREVIEW_NOTE } from '../data/bookings'
import type { Booking } from '../types'

describe('BOOKINGS data integrity', () => {
  it('every booking has all required fields', () => {
    for (const booking of BOOKINGS) {
      const fields: (keyof Booking)[] = ['id', 'title', 'meta', 'status', 'tone']
      for (const field of fields) {
        expect(field in booking).toBe(true)
        expect(booking[field]).not.toBeUndefined()
        expect(booking[field]).not.toBeNull()
      }
    }
  })

  it('every booking tone is a valid BookingTone value', () => {
    const validTones = ['ok', 'wait', 'sent']
    for (const booking of BOOKINGS) {
      expect(validTones).toContain(booking.tone)
    }
  })

  it('every booking has a non-empty id', () => {
    for (const booking of BOOKINGS) {
      expect(typeof booking.id).toBe('string')
      expect(booking.id.length).toBeGreaterThan(0)
    }
  })

  it('every booking has a non-empty title', () => {
    for (const booking of BOOKINGS) {
      expect(typeof booking.title).toBe('string')
      expect(booking.title.length).toBeGreaterThan(0)
    }
  })

  it('BOOKINGS_PREVIEW_NOTE is defined as a non-empty string', () => {
    expect(typeof BOOKINGS_PREVIEW_NOTE).toBe('string')
    expect(BOOKINGS_PREVIEW_NOTE.length).toBeGreaterThan(0)
  })
})
