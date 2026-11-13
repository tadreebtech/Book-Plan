/**
 * Button — shared call-to-action element.
 *
 * Renders an <a> when `href` is provided, otherwise a <button>.
 * Variants: primary | ghost | light. Sizes: md (default) | sm.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './Button.css'

/** Visual style of the button. */
export type ButtonVariant = 'primary' | 'ghost' | 'light'

/** Height/padding preset. */
export type ButtonSize = 'md' | 'sm'

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  /** When set, the component renders an anchor instead of a button. */
  href?: string
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  children?: ReactNode
}

export default function Button({
  href,
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  const classes = ['btn', `btn--${variant}`, size === 'sm' && 'btn--sm', className]
    .filter(Boolean)
    .join(' ')

  if (href) {
    return (
      <a className={classes} href={href} {...(rest as ButtonHTMLAttributes<HTMLAnchorElement>)}>
        {children}
      </a>
    )
  }

  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  )
}
