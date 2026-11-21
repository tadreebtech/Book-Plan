/**
 * SectionHeader — shared heading block used by every content section.
 *
 * Layout: eyebrow + h2 on the left, supporting text on the right.
 * `title` accepts a node so sections can control their own line breaks.
 */

import type { ReactNode } from 'react'
import './SectionHeader.css'

export interface SectionHeaderProps {
  /** Small uppercase label above the title. */
  eyebrow: string
  /** Section heading; accepts a node so callers can control line breaks. */
  title: ReactNode
  /** Optional supporting paragraph shown on the right. */
  lead?: string
}

export default function SectionHeader({ eyebrow, title, lead }: SectionHeaderProps) {
  return (
    <div className="section__head">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {lead && <p className="section__lead">{lead}</p>}
    </div>
  )
}
