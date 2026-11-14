# Book&Plan

Book&Plan is a static public landing page for a booking platform. It presents the product, its booking flow, resource categories, provider onboarding, and a demonstration of the "My bookings" interface.

The current implementation is a frontend-only landing page. All page content is stored as static TypeScript data in `src/data/`. There is no backend, database, authentication, or client-side routing configured.

## 1. Project Overview

Book&Plan aims to provide a single platform for booking premises, services, and venues. The landing page explains how users can find a resource, send a booking request, and track its status. It also shows how multiple bookings can be combined into an event plan.

Implemented functionality:

- Responsive public landing page.
- Shared layout with header and footer.
- Seven landing-page sections rendered in a fixed order.
- Static demo booking data with confirmed, pending, and sent statuses.
- Reusable UI components.
- Design tokens and responsive CSS.
- Unit tests for booking data integrity.

Planned or not implemented:

- Backend/API integration.
- Real user accounts and authentication.
- Real booking creation and status updates.
- Client-side routing and additional pages.
- Filtering in the bookings card tabs.
- Component-level tests.

## 2. Main Features

Landing-page sections, in render order:

| Section | Component | Data source | Purpose |
| --- | --- | --- | --- |
| Hero | `HeroSection` | `src/data/bookings.ts` | Headline, CTAs, and a preview booking card |
| Categories | `CategoriesSection` | `src/data/categories.ts` | Featured university resources plus services and venues |
| How to book | `HowItWorksSection` | `src/data/steps.ts` | Three-step booking flow |
| My bookings | `BookingsSection` | `src/data/bookings.ts` | Full booking card with status pills |
| For events | `EventsSection` | `src/data/eventPlan.ts` | Event planning callout and plan preview |
| For providers | `ProvidersSection` | `src/data/providers.ts` | Three provider onboarding steps |
| Final CTA | `CtaSection` | None | Final registration/login call to action |

Additional implemented features:

- Sticky header with logo, navigation links, and login/register buttons.
- Footer with compact navigation and tagline.
- Booking status pills with `ok`, `wait`, and `sent` tones.
- Reusable `Button`, `Logo`, `SectionHeader`, `StatusPill`, and `Lines` components.
- Responsive layout for desktop, tablet (`<= 1024px`), and mobile (`<= 640px`).
- Google Fonts loaded in `index.html`: Inter and Playfair Display.

## 3. Technology Stack

| Technology | Version | Usage |
| --- | --- | --- |
| React | 19.3.1 | UI components |
| React DOM | 19.3.1 | Browser rendering |
| Vite | 7.3.7 | Development server and production build |
| TypeScript | 7.0.2 | Type checking for `.ts` and `.tsx` files in `src`; strict mode enabled. `.jsx` files are not type-checked because `checkJs` is false |
| JavaScript | ES2022+ | Runtime language; `allowJs` is enabled |
| CSS | Plain CSS | Component and global styles |
| ESLint | 10.13.0 | Linting for `.js` and `.jsx` files |
| Prettier | 3.9.10 | Formatting checks |
| Vitest | 5.0.5 | Unit tests |
| happy-dom | 21.0.4 | Vitest test environment |

Supporting development dependencies include `@vitejs/plugin-react`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`, `@types/node`, `@types/react`, and `@types/react-dom`.

## 4. Project Structure

```text
Book_plan/
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
├── vitest.config.js
├── eslint.config.js
├── tsconfig.json
├── tsconfig.node.json
├── .prettierrc.json
├── .gitignore
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── main.jsx
│   ├── App.tsx
│   ├── App.jsx
│   ├── assets/
│   │   └── logo-mark.svg
│   ├── components/
│   │   ├── bookings/
│   │   │   ├── BookingsCard.css
│   │   │   └── BookingsCard.tsx
│   │   ├── layout/
│   │   │   ├── Footer.css
│   │   │   ├── Footer.tsx
│   │   │   ├── Header.css
│   │   │   └── Header.tsx
│   │   ├── sections/
│   │   │   ├── BookingsSection.jsx
│   │   │   ├── BookingsSection.tsx
│   │   │   ├── CategoriesSection.css
│   │   │   ├── CategoriesSection.jsx
│   │   │   ├── CategoriesSection.tsx
│   │   │   ├── CtaSection.css
│   │   │   ├── CtaSection.jsx
│   │   │   ├── CtaSection.tsx
│   │   │   ├── EventsSection.css
│   │   │   ├── EventsSection.jsx
│   │   │   ├── EventsSection.tsx
│   │   │   ├── HeroSection.css
│   │   │   ├── HeroSection.jsx
│   │   │   ├── HeroSection.tsx
│   │   │   ├── HowItWorksSection.css
│   │   │   ├── HowItWorksSection.jsx
│   │   │   ├── HowItWorksSection.tsx
│   │   │   ├── ProvidersSection.css
│   │   │   ├── ProvidersSection.jsx
│   │   │   └── ProvidersSection.tsx
│   │   └── ui/
│   │       ├── Button.css
│   │       ├── Button.tsx
│   │       ├── Lines.tsx
│   │       ├── Logo.css
│   │       ├── Logo.tsx
│   │       ├── SectionHeader.css
│   │       ├── SectionHeader.tsx
│   │       ├── StatusPill.css
│   │       └── StatusPill.tsx
│   ├── data/
│   │   ├── bookings.ts
│   │   ├── categories.ts
│   │   ├── eventPlan.ts
│   │   ├── navigation.ts
│   │   ├── providers.ts
│   │   └── steps.ts
│   ├── pages/
│   │   ├── HomePage.jsx
│   │   └── HomePage.tsx
│   ├── styles/
│   │   ├── base.css
│   │   └── tokens.css
│   ├── tests/
│   │   └── bookings.test.ts
│   └── types/
│       └── index.ts
├── book & plan/
│   ├── 00 · Палитры и пояснения.png
│   └── 01 · Зелёный/
│       └── Сад/
│           ├── Desktop 1440.png
│           └── Mobile 390.png
└── data_icon/
    └── 01 · Зелёный/
        └── Сад/
            └── 09/
                └── Знак/
                    └── календарь.svg
```

Application entry point:

- `index.html` loads `/src/main.tsx`.
- `src/main.tsx` imports `./App`, which resolves to `src/App.tsx` because TypeScript extensions are resolved before JavaScript extensions.
- `src/App.tsx` renders the header, `HomePage`, and footer. `HomePage.tsx` renders the section `.tsx` components.
- The `.jsx` files are unused duplicates. Their contents are identical to the corresponding `.tsx` files, except `src/main.jsx`, which has a shorter root-element check. They are still matched by the ESLint configuration but are not part of the active Vite entry graph.

Directory purposes:

- `src/components`: reusable and section-level React components. Section components own their CSS files.
- `src/pages`: page-level components. `HomePage` composes all landing sections.
- `src/data`: static content consumed by components.
- `src/styles`: global design tokens and base styles.
- `src/assets`: runtime image and SVG assets imported by components.
- `public`: static files served as-is, including the favicon.
- `src/tests`: Vitest tests.
- `src/types`: shared TypeScript interfaces and types.
- `book & plan` and `data_icon`: Figma/design reference assets and source artwork. They are not imported by the Vite application except for the copied logo mark.

## 5. Prerequisites

- Node.js `^22.13.0` or `>=24.0.0`, as required by the installed versions of Vite, ESLint, and Vitest. The project was tested with Node.js `v24.11.1`.
- npm `8.0.0` or newer, as required by Rollup. The project was tested with npm `11.6.2`.

## 6. Installation and Setup

Clone the repository and install dependencies:

```bash
npm install
```

## 7. Running the Development Server

Start the Vite development server:

```bash
npm run dev
```

Vite prints a local URL in the terminal. Open that URL in a browser. The default Vite URL is usually `http://localhost:5173`.

## 8. Available Scripts

| Script | Command | Description |
| --- | --- | --- |
| `dev` | `npm run dev` | Start the Vite development server |
| `build` | `npm run build` | Build the production bundle |
| `preview` | `npm run preview` | Preview the production build locally |
| `lint` | `npm run lint` | Run ESLint on `.js` and `.jsx` files |
| `format:check` | `npm run format:check` | Check formatting with Prettier |
| `test` | `npm run test` | Run Vitest tests once |

## 9. Testing and Code Quality

Run ESLint:

```bash
npm run lint
```

Check Prettier formatting:

```bash
npm run format:check
```

Run Vitest tests:

```bash
npm run test
```

Run TypeScript type checking. There is no dedicated npm script for this; use:

```bash
npx tsc --noEmit
```

This command completes successfully in the current project and checks the `.ts` and `.tsx` files included by `tsconfig.json`.

The existing test file is `src/tests/bookings.test.ts`. It validates that every booking in `src/data/bookings.ts` has the required `Booking` fields, a valid tone, non-empty `id` and `title` values, and that `BOOKINGS_PREVIEW_NOTE` is a non-empty string.

Note: ESLint is configured for `**/*.{js,jsx}` only. TypeScript files are type-checked by `tsc` instead.

## 10. Build for Production

Create the production build:

```bash
npm run build
```

The production output is generated in the `dist/` directory.

## 11. Development Workflow

The repository currently has one branch, `main`, with no commits yet. No `dev` branch, CI pipeline, branch protection, or deployment configuration was verified.

Recommended local workflow:

1. Install dependencies with `npm install`.
2. Start the development server with `npm run dev`.
3. Edit components, data, styles, or configuration as needed.
4. Run `npm run lint`, `npm run format:check`, `npm run test`, and `npx tsc --noEmit`.
5. Run `npm run build` to verify the production bundle.
6. Use `npm run preview` to inspect the built output.

## 12. Design and Assets

Design tokens are defined in `src/styles/tokens.css` and provide colors, fonts, radii, and booking status colors. The active palette is `01 · Зелёный / Сад`. Switching palettes requires changing the `--green*` and `--page` values.

Base styles in `src/styles/base.css` provide the reset, global typography, `.container`, `.section`, and responsive breakpoints.

Component styles are stored next to their components and use BEM-style class names. Global styles are imported first in `src/main.tsx`, followed by component styles.

Runtime assets:

- `src/assets/logo-mark.svg`: Book&Plan logo mark used by `Logo`.
- `public/favicon.svg`: browser favicon, using the same logo mark.

Design reference assets:

- `book & plan/`: palette overview and desktop/mobile mockups.
- `data_icon/`: source SVG artwork for the logo mark.

Fonts are loaded from Google Fonts in `index.html`, so an internet connection is required on first load.

## 13. Future Improvements

These are potential improvements and are not implemented:

- Add a backend/API layer and replace static data in `src/data/`.
- Add client-side routing and additional pages.
- Implement the visual booking filters in `BookingsCard`.
- Add real authentication and registration flows.
- Expand automated tests to cover components and rendering.
- Add localization support if multiple languages are needed.
- Switch the color palette using the tokens in `src/styles/tokens.css`.
