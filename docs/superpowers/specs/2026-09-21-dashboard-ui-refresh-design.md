# BottleIQ Dashboard UI Refresh Design

Date: 2026-09-21
Status: Approved design

## Objective

Refresh the BottleIQ dashboard as the first step toward a possible application-wide UI update. The dashboard should help an independent liquor-store owner identify and act on the week's most important inventory decisions quickly on both desktop and mobile.

The work will reorganize and restyle data already returned by the dashboard API. It will not add metrics, change analytics, or require backend work.

## Design Direction

The selected direction is **operational clarity**: calm, trustworthy, action-oriented, and recognizably BottleIQ. The existing deep-green identity and warm neutral background remain, while hierarchy, spacing, typography, responsive behavior, feedback states, and accessibility receive a focused upgrade.

The dashboard is an action-first command center rather than a dense analytics report. Charts and secondary analysis will not displace the three decisions that matter most:

1. Build this week's order.
2. Prevent likely stockouts.
3. Free cash tied up in slow or dead inventory.

## Information Architecture

### Desktop

The dashboard will use the following order:

1. **Context header** — greeting, concise orientation, current store context from the workspace shell, data freshness, and access to data updates.
2. **Decision cards** — three linked cards for the weekly order, stockout risk, and trapped cash. The weekly order is visually dominant; the others use restrained warning and sage treatments.
3. **Data-quality notice** — shown only when missing costs make the order total incomplete. It stays near the affected metric and links to the repair workflow.
4. **Action queues** — two panels: urgent products to order and products for which buying should pause. Each row exposes the minimum information necessary to understand and take the next step.
5. **Inventory-health summary** — snapshot date, total inventory value, product count, and link to the complete inventory.

### Mobile

The same content will stack in decision priority. The weekly order remains first, followed by stockout risk, trapped cash, the conditional data notice, action queues, and the inventory summary.

Mobile requirements:

- No horizontal page scrolling at 375px.
- Primary actions do not depend on hover.
- Interactive targets are at least 44px in either height or combined clickable area where practical.
- Metadata wraps or simplifies rather than shrinking below a readable size.
- Financial values and product names remain visually distinct.

## Visual System

### Color

- Preserve deep forest green as the primary brand and action color.
- Use a warm ivory page background and white or near-white surfaces.
- Use muted sage for supportive information.
- Reserve amber for actual attention states, including missing data and stockout risk.
- Keep normal text at a minimum 4.5:1 contrast ratio.
- Do not use color as the sole status indicator; pair it with text and Lucide icons.

### Typography

- Continue with a clean sans-serif interface suited to operational software.
- Strengthen scale contrast between page headings, decision values, card labels, and supporting copy.
- Use tabular numerals for currency and numeric metrics where available.
- Keep body text at least 16px on mobile and use comfortable line height.

### Surfaces and Motion

- Use consistent borders, radii, and restrained shadows across cards and panels.
- Use 150–250ms color, border, and shadow transitions for interaction feedback.
- Avoid transforms that shift layout or make operational cards feel playful.
- Disable nonessential transitions under `prefers-reduced-motion`.

### Icons and Actions

- Continue using Lucide as the single icon family.
- Use consistent icon sizes and clearly labeled actions.
- Provide visible keyboard focus rings.
- Preserve existing navigation destinations and inventory-filter links.

## Components

The refreshed dashboard should be implemented as focused, reusable pieces rather than expanding the page component indefinitely:

- `DashboardSkeleton` reserves the final layout while dashboard data loads.
- `DecisionCard` presents one primary decision, its value, context, icon, and destination.
- `DashboardNotice` explains missing-cost consequences and provides the repair action.
- `ActionQueue` owns a titled group of product actions and its zero-result state.
- `ActionRow` presents product identity, decision context, supporting value, and destination.
- `InventorySummary` presents freshness, total value, catalog size, and the inventory link.

Components may remain local to the dashboard when they have no current consumer. Shared tokens and genuinely reusable interaction styles belong in the existing UI and global stylesheet structure. The refactor must not change navigation behavior or API ownership of calculations.

## Data Flow

The page continues to request `Dashboard` data from `/dashboard?store_id=<store id>` through `useResource`. The store and user continue to come from `useWorkspace`.

All displayed values are derived from existing response fields. The combined trapped-cash value remains `slow_value + dead_value`. Existing formatting helpers remain authoritative for currency and decimals. Links continue to route to Smart Orders, filtered inventory views, alerts, imports, inventory, and product detail pages.

No client-side business calculations beyond existing display composition will be introduced.

## UI States

### Loading

Use a dashboard-shaped skeleton with reserved blocks for the title, decision cards, queues, and summary. It must expose an accessible loading status and avoid unexpected layout shift when data arrives.

### Error

Retain the existing accessible alert semantics and retry behavior. Its presentation should match the refreshed surfaces and spacing.

### Empty Catalog

Show a concise onboarding state explaining that inventory, sales, and purchase data unlock recommendations. Provide one prominent link to the existing import workflow.

### Missing Costs

When `missing_cost_count` is positive, explain that affected products are excluded from order totals and provide a direct link to resolve the issue. Singular and plural text must remain grammatically correct.

### Empty Queues

An empty reorder queue should explicitly state that nothing needs ordering now. An empty slow-stock queue should state that no slow inventory needs attention. Empty states should feel reassuring without hiding data-quality problems.

## Accessibility and Interaction Requirements

- Keyboard order follows visual order.
- Every interactive element has a visible focus state.
- Icon-only controls retain an accessible name.
- Links and buttons communicate their purpose without relying on surrounding layout.
- Touch targets are sized for mobile use.
- Statuses use icon/text in addition to color.
- Loading and error feedback use appropriate status or alert semantics.
- Reduced-motion preferences are respected.
- The page remains usable at 200% browser zoom without losing actions.

## Verification

Implementation is complete when:

- Existing dashboard data and navigation behavior remain correct.
- Component or browser assertions are updated for intentionally changed labels and structure.
- Frontend lint, formatting check, type checking, tests, and production build pass.
- The dashboard is visually inspected at 375px, 768px, 1024px, and 1440px widths.
- No horizontal page scroll appears at the tested widths.
- Keyboard focus, loading, error, empty, missing-cost, and zero-result states are checked.
- Reduced-motion rules are present for new transitions.
- The UI uses Lucide icons only and does not introduce emoji icons.

## Out of Scope

- Backend or analytics changes.
- New dashboard metrics.
- Automatic purchasing or supplier submission.
- Dark mode.
- Full redesigns of inventory, Smart Orders, alerts, imports, settings, authentication, or marketing pages.
- Rebranding, a new logo, or an unrelated navigation rewrite.

The dashboard components and visual tokens should nevertheless be structured so a later full-app refresh can extend them without redoing this work.
