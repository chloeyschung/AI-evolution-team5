# Briefly Visual Language Guide

**Status:** Canonical visual-branding guide  
**Audience:** Designers, frontend engineers, LLM agents  
**Scope:** Visual identity, brand identity, key visual, visual language, component-level styling rules  
**Out of scope:** Accessibility, keyboard UX, form validation, performance, and interaction-only guidance

---

## 1. Objective

The goal is not to mix recognizable traits from Palantir, Sendbird, Claude, and Apple into a collage.

The goal is to build **one coherent visual language** for Briefly.

That language must feel:

- simple enough to read in one glance
- strong enough to be recognizable without a logo
- warm enough to remove guilt and friction
- precise enough to support dense information work

Briefly is not a storage app. It is a **consumption rhythm product**.  
Everything visual must reinforce that: less backlog, less guilt, more signal, more momentum.

---

## 2. Method

This guide follows a de-blur-style branding sequence:

1. **Strategy**
2. **Brand Identity**
3. **Key Visual**
4. **Visual System**
5. **Component Grammar**
6. **Surface Application**

No component styling should happen before the identity and key visual are clear.

---

## 3. Strategic Foundation

Derived from [docs/mps.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/mps.md:1) and [docs/MANIFEST.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/MANIFEST.md:1):

- Briefly converts the "information cemetery" into a lightweight reading flow.
- Briefly prioritizes **consumption over collection**.
- Briefly must feel **guilt-free**, **bite-sized**, and **rewarding** rather than managerial or punishing.

The brand therefore should not feel:

- archival
- academic
- ornamental
- nostalgic
- bronze, mustard, sepia, parchment-like, or "library" coded

It should feel:

- modern
- calm
- bright
- deliberate
- fast without anxiety

---

## 4. Unified Brand Language

### 4.1 Name

The Briefly visual language is:

## **Quiet Momentum**

This is the single unifying phrase.

It means:

- **Quiet**: uncluttered, light, calm, high-trust
- **Momentum**: forward-moving, efficient, progressive, never stagnant

This is not "warm minimalism" plus "enterprise density" plus "cute detail."  
Those are source influences.  
**Quiet Momentum** is the actual output language.

### 4.2 Brand Personality

- Calm, not sleepy
- Friendly, not playful
- Precise, not severe
- Modern, not futuristic
- Strong, not loud

---

## 5. Visual Identity

### 5.1 Core Brand Promise

**From saved noise to usable signal.**

### 5.2 Emotional Goal

A user should feel:

- "I can get through this"
- "This is lighter than my backlog"
- "This product is on my side"

### 5.3 Visual Positioning

If Apple is "clarity through restraint," and Palantir is "clarity through structure," Briefly is:

**clarity through structured relief**

That means:

- structure is visible
- density is manageable
- the product removes emotional weight

---

## 6. Key Visual

### 6.1 Main Motif

The Briefly key visual is a **guided flow**.

Not stacks, shelves, vaults, books, temples, archives, folders, or piles.

The motif should express:

- compression
- direction
- release
- forward motion

Accepted visual metaphors:

- a narrow ribbon of signal moving through open space
- a soft directional beam
- layered planes converging into one clean axis
- a card stream becoming one readable lane

Rejected visual metaphors:

- ancient library
- study desk nostalgia
- leather, brass, parchment, amber-heavy palettes
- scrapbook, note-board, knowledge attic, or cabinet metaphors

### 6.2 Composition Rule

Every branded surface needs one dominant visual idea only.

Examples:

- auth: one signal lane + one promise + one action
- dashboard: one structured hero plane + one primary work area
- empty state: one emblematic motion path + one clear next step

Never use multiple competing decorative ideas on the same screen.

---

## 7. Color System

### 7.1 Color Principle

Briefly uses **cool clarity on warm light**.

That is the brand signature.

- The product should not feel cold-white clinical.
- The product should not feel beige, bronze, or sepia.
- The warmth must live in the light neutrals, not in the primary action color.

### 7.2 Canonical Palette

Use these as the primary brand anchors:

- `Canvas`: `#F6F7FB`
- `Surface`: `#FFFFFF`
- `Surface Muted`: `#EEF2F8`
- `Text Primary`: `#1C2127`
- `Text Secondary`: `#5F6B7C`
- `Text Muted`: `#738091`
- `Primary`: `#2D72D2`
- `Primary Strong`: `#1F5FBF`
- `Info`: `#147EB3`
- `Success`: `#238551`
- `Danger`: `#CD4246`

### 7.3 Strict Color Rules

- The **primary CTA** must be blue-based.
- Warmth must come from the background and light treatment, not from golden CTAs.
- Gold/amber may exist only as a microscopic editorial accent, not a dominant product color.
- Purple must not become a parallel brand accent.
- Teal and green are semantic colors, not identity colors.

### 7.4 Deprecated

The following are explicitly deprecated as leading visual identity colors:

- `#B98B24`
- `#CFA03B`
- any mustard, ochre, bronze, brass, or "old paper" tones

---

## 8. Geometry System

This is where the language becomes product-specific rather than generic.

### 8.1 Corner Family

Briefly corners are **soft-square**, not bubbly and not razor-sharp.

Use a single family:

- small: `6px`
- medium: `8px`
- large: `12px`
- panel: `16px`

Rules:

- never mix rounded pills and sharp cards without semantic reason
- outer containers should be slightly rounder than inner controls
- nested corners must reduce inward

### 8.2 Directional Angle

The brand highlight angle is **10deg to 14deg**.

Use this for:

- subtle gradients
- directional gleam
- hero surfaces
- active strip or emphasis plane

Do not use random radial rainbow gradients.  
Do not use fully horizontal generic SaaS gradients when a directional plane is intended.

### 8.3 Line and Border Discipline

- default border: `1px`
- subtle surfaces use tinted borders, not thick outlines
- no heavy boxed frames unless the box is the interaction target

The feeling should be engineered, not decorated.

---

## 9. Typography

### 9.1 Principle

The type system should carry confidence through discipline, not through novelty.

### 9.2 Family

Use a restrained product type system:

- Display and body: `Geist`
- Data/meta/technical labels: `Geist Mono`

Do not introduce a second expressive display font unless there is a full system decision behind it.

### 9.3 Hierarchy

- Headlines: compact, controlled, high contrast
- Utility labels: explicit, small, structured
- Data and counts: tabular numerals where comparison matters

### 9.4 Copy Tone

- Branded surfaces may sound warm and relieving
- Product surfaces must sound operational and clear
- The language should never sound like a study app from 2016 or a productivity sermon

---

## 10. Layout Language

### 10.1 Overall Rule

Briefly surfaces should feel like **open planes with one decisive lane of attention**.

Not:

- card mosaics
- dashboard wallpaper
- decorative chrome around every region

### 10.2 App Shell

The shell should communicate:

- stable navigation
- light structure
- controlled density

The rail and top bar should feel like one family:

- muted, architectural, supportive
- never louder than the work surface

### 10.3 Work Surfaces

Inbox, archive, analytics, and dashboard content areas should be:

- table-first or list-first
- low-chrome
- high legibility
- structurally branded, not cosmetically branded

That means branding appears in:

- tone
- geometry
- highlight planes
- key visual rhythm

Not in:

- repeated logos
- decorative stickers
- random gradients

---

## 11. Component Grammar

This section is written for LLM agents. These rules must be followed directly.

### 11.1 Buttons

- Primary buttons are blue-led and slightly directional
- Use a 10deg-14deg gradient only when the button is the main action
- Border radius: `8px`
- Weight: medium-strong, never extra-bold by default
- No gold CTA buttons
- No purple CTA buttons
- No glassmorphism buttons

Primary button behavior:

- still when idle
- slight lift on hover
- sharper shadow on focus/active

### 11.2 Inputs

- Inputs are quiet and architectural
- Background should sit just above the canvas, not float dramatically
- Borders should be visible but low-noise
- Focus state must use the brand blue ring
- Inputs should not look playful

### 11.3 Cards

- Cards are allowed only when the card itself is the working unit
- Cards must not be used as default wrappers for every section
- Card backgrounds should stay clean and mostly flat
- Card decoration should be subtle: one edge tint, one directional highlight, one restrained shadow

If the same screen already has a hero card, avoid another equally dominant card language beneath it.

### 11.4 Tables and Lists

- These are the heart of the product surface
- Favor readable structure over decorative summary cards
- Use mono where scanning comparison matters
- Action clusters must be compact and calm
- Row hover should feel like signal emphasis, not color flooding

### 11.5 Navigation Rail

- The rail is the structural spine
- It should feel refined and composed
- The active item should look selected through shape and plane, not through loud color alone
- Rail branding should feel embedded, not pasted on

### 11.6 Top Bar

- The top bar is a light control plane, not a marketing banner
- Search must feel central and frictionless
- User/session controls should visually recede

### 11.7 Auth Surfaces

- Auth is the most permissive branded surface
- It may include:
  - a monogram
  - a signal-flow motif
  - one warmth-bearing line of copy
- It may not become a generic centered white card on a vague gradient

### 11.8 Empty States

- Empty states should be relieving, not sad
- Use one composed visual motif
- Pair it with one practical next step

### 11.9 Visual Polish Contract

- Primary action color must stay blue-led and use `--color-primary` or `#2D72D2` as the default product CTA signal.
- Warm accent usage must stay restricted to secondary or editorial emphasis; it may not replace blue as the default CTA fill.
- Deprecated gold or mustard tones are not allowed as identity colors and should not appear in product CTA treatment.
- Auth layouts must keep at least `8px` separation between stacked controls and use full-width primary actions.
- Each viewport should present one dominant anchor surface only; auth uses the signal lane, shell uses the rail/top bar family, and work surfaces use the main reading plane.
- If a screen starts to feel like multiple competing cards or decorative ideas, remove a layer before adding styling.

---

## 12. Motion Language

Motion must express Quiet Momentum.

That means:

- no floaty generic startup animations
- no ornamental shimmer for its own sake
- no bouncy toy motion

Use only three motion categories:

1. **Arrival**  
   Soft staged reveal for hero or first-view structure

2. **Progression**  
   Drawer, table, or panel transition that clarifies where attention moves

3. **Affordance**  
   Hover/focus/active refinements that sharpen confidence

Timing:

- fast enough to feel decisive
- slow enough to feel calm

---

## 13. Visual Do / Don't

### Do

- build around one dominant visual idea per surface
- use negative space as part of the brand
- make blue the reliable action signal
- make warmth live in light and tone, not in vintage color choices
- keep surfaces crisp, calm, and intentional

### Don't

- simulate "knowledge" with library aesthetics
- use amber/mustard as a shortcut to warmth
- over-brand every surface with badges, marks, and slogans
- mix enterprise density, playful UI, and editorial ornament in parallel
- use multiple unrelated visual metaphors on one screen

---

## 14. LLM Agent Execution Rules

When an LLM agent creates or edits UI for Briefly, it must:

1. start from the brand language `Quiet Momentum`
2. preserve a single primary color identity
3. treat warmth as atmospheric, not nostalgic
4. prefer one strong visual move over many small decorative moves
5. reduce card nesting before adding more styling
6. preserve soft-square geometry across all surfaces
7. use utility-first copy on product screens
8. ensure auth, dashboard, extension, and empty states all feel like the same product

If a proposed UI looks like a fusion board rather than one authored language, it is wrong.

---

## 15. References

These are reference directions, not style fragments to copy literally.

- Briefly strategy sources:
  - [docs/mps.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/mps.md:1)
  - [docs/MANIFEST.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/MANIFEST.md:1)
- Implementation records:
  - [docs/records/ui-brand-unification-bulk-refactor-asis-to-be-2026-04-17.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/records/ui-brand-unification-bulk-refactor-asis-to-be-2026-04-17.md:1)
  - [docs/records/ui-visual-polish-asis-to-be-2026-04-18.md](/media/younghwan/3006F86D14CC96B4/project/Briefly/docs/records/ui-visual-polish-asis-to-be-2026-04-18.md:1)
- Palantir Blueprint variables:
  - https://raw.githubusercontent.com/palantir/blueprint/develop/packages/core/src/common/_variables.scss
- Sendbird UIKit React theming:
  - https://sendbird.com/docs/chat/uikit/v3/react/theme-and-style-resources/color-resources
- Claude MCP Apps design guideline:
  - https://claude.com/docs/connectors/building/mcp-apps/design-guidelines
- de-blur column hub:
  - https://www.de-blur.com/column
- de-blur branding process:
  - https://www.de-blur.com/column/branding-process
- de-blur key visual:
  - https://www.de-blur.com/column/about-keyvisual
- de-blur brand web design:
  - https://www.de-blur.com/column/brand-web-design
