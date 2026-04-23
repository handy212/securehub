# Design System: Secure Intelligence & Tonal Depth

## 1. Overview & Creative North Star: "The Digital Concierge"
This design system moves away from the utilitarian, "dashboard-heavy" look of traditional security apps toward a high-end editorial experience. Our Creative North Star is **The Digital Concierge**: an interface that feels protective yet invisible, sophisticated yet effortless.

We reject the rigid, boxy constraints of standard IoT apps. Instead, we embrace **Tonal Layering** and **Asymmetric Breathing Room**. By utilizing varying densities of the `surface` tokens and purposeful white space, we create a sense of architectural depth. The goal is to make the user feel like they are looking through a window into their home, rather than looking at a control panel.

## 2. Colors & Atmospheric Depth
Our palette is rooted in the depth of `primary` (#080A10) and the warmth of `surface` (#FAF9F6). We use these to create a "Tactile Digital" feel.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or containment. Boundaries must be defined solely through:
- **Background Color Shifts:** Placing a `surface-container-low` section against a `surface` background.
- **Tonal Transitions:** Using subtle shifts between `surface-container-lowest` and `surface-container-high`.

### Surface Hierarchy & Nesting
Treat the UI as physical layers—like stacked sheets of fine paper or frosted glass. 
- **Base Layer:** `surface`
- **Sectioning:** `surface-container-low` for large groupings.
- **Priority Interaction:** `surface-container-highest` for active or focused states.
- **Floating Intelligence:** `surface-container-lowest` (pure white) for critical cards that need to "pop" off the page.

### The "Glass & Gradient" Rule
To elevate the experience, use **Glassmorphism** for floating controllers (e.g., a thermostat slider or camera overlay). 
- **Specs:** Use `surface` at 80% opacity with a 20px - 32px backdrop blur. 
- **Signature Textures:** Main CTAs (like "Arm Home") should not be flat. Apply a subtle linear gradient from `primary` (#080A10) to `primary-container` (#1F2127) at a 45-degree angle to provide a satin-like finish.

## 3. Typography: Editorial Authority
We use **Inter** as our typographic engine to provide a clean, Swiss-inspired aesthetic that conveys precision and reliability.

- **Display Scale (`display-lg` to `display-sm`):** Reserved for atmospheric data—like the current temperature or "System Armed" status. These should feel like headlines in a premium magazine.
- **Headline & Title:** Used to anchor sections. Pair `headline-sm` with a `surface-container` background to create a clear visual anchor without needing a line.
- **Body & Labels:** All body text must use `on-surface-variant` to reduce visual noise, switching to `on-surface` only for active user input or critical alerts.
- **Hierarchy through Contrast:** We create importance not by increasing font weight, but by shifting from `on-surface-variant` to `primary`.

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are a fallback; tonal layering is the standard.

### The Layering Principle
Depth is achieved by "stacking." A card should be `surface-container-lowest` sitting on a `surface-container-low` background. This creates a soft, natural lift that feels integrated into the architecture.

### Ambient Shadows
When an element must "float" (e.g., a modal or a primary action button):
- **Blur:** 40px to 60px.
- **Opacity:** 4% - 8%.
- **Tint:** The shadow color must be a tinted version of `on-surface` (#1B1C1A), never a generic black or grey.

### The "Ghost Border" Fallback
If a border is required for accessibility (e.g., in high-contrast light mode), use a **Ghost Border**:
- **Token:** `outline-variant`
- **Opacity:** 15% maximum. 
- **Forbid:** 100% opaque, high-contrast borders are strictly prohibited.

## 5. Components

### Buttons & Interaction
- **Primary:** Gradient fill (`primary` to `primary-container`), `radius-md` (1.5rem). The text is `on-primary`.
- **Secondary:** Glassmorphic fill (80% `surface` + blur). No border.
- **Tertiary:** Text only, using `primary` color with `title-sm` styling.

### Input Fields & Controls
- **Text Inputs:** Use `surface-container-high` as the background. No border. Upon focus, shift the background to `surface-container-highest`.
- **Checkboxes & Radios:** Use `secondary` (#366B00) for "Secure" states. Use a `radius-sm` (0.5rem) even for "square" elements to maintain the system's softness.

### Cards & Lists
- **Forbid Dividers:** Never use a line to separate list items. Use 16px to 24px of vertical white space or alternating tonal shifts (e.g., a `surface-container-low` card next to a `surface` card).
- **Security Cards:** For status updates, use a left-accented "Tonal Bar" (a 4px vertical strip of `secondary` or `error`) instead of coloring the whole card.

### Additional Contextual Components
- **Status Biometrics:** A circular "breathing" glow using `secondary` to indicate the system is live and monitoring.
- **The "Safety Shade":** A full-screen overlay using `tertiary-container` with 10% opacity when the system is in "Urgent" mode, shifting the entire app's atmosphere.

## 6. Do's and Don'ts

### Do
- **Do** use `xl` (3rem) border radius for large hero containers to create a modern, friendly feel.
- **Do** allow content to bleed off-edge in carousels to suggest continuity.
- **Do** use `on-secondary-container` for text on green "Secure" badges to ensure high-end color harmony.

### Don't
- **Don't** use pure black (#000000). Use `primary` (#080A10) for maximum depth.
- **Don't** use standard Material Design "Drop Shadows." If it looks like a default shadow, it is wrong.
- **Don't** use more than three font sizes on a single screen. Rely on color and weight (Inter Regular vs. Medium) to differentiate.
- **Don't** use icons without sufficient padding; every icon should have a "safe zone" of at least 12px.