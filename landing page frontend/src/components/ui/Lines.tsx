/**
 * Lines — renders an array of strings with hard line breaks.
 *
 * Some headings must break on a specific word to match the design, so their
 * copy is stored as an array of lines and rendered with <br /> between them.
 */

import { Fragment } from 'react'

export interface LinesProps {
  /** Lines of text; each entry is rendered on its own line. */
  lines: string[]
}

export default function Lines({ lines }: LinesProps) {
  return lines.map((line, index) => (
    <Fragment key={line}>
      {index > 0 && <br />}
      {line}
    </Fragment>
  ))
}
