# Visual QA Issues

Reviewed by Marcus (UI Critic)

## Issues Found:

### 1. Vibe Mismatch & Gradient Usage Violations
- **File**: `DESIGN TOKENS`
- **Issue**: The `pageBg` token uses `bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900`. This applies a full-viewport gradient, directly violating the rule: "Gradients should be < 20% of viewport". A full-page gradient can be overwhelming and detract from content focus.
- **Issue**: The `primaryButton` token uses `bg-gradient-to-r from-purple-500 to-pink-500`. This combination is explicitly flagged as "Avoid generic purple-blue or purple-pink combinations" in the design guidelines. While 'modern_gradient' allows gradients, they should be more unique or subtle.

### 2. Transitions & Animations - 'transition-all' Usage
- **File**: `DESIGN TOKENS`
- **Issue**: Both `primaryButton` and `secondaryButton` tokens use `transition-all`. The guideline states: "Avoid 'transition: all' (use specific properties)". Using `transition-all` can be inefficient and lead to unintended animations on properties that don't need to transition.

### 3. Design Token Compliance - Ad-hoc Styling & Missing Token Application
- **File**: `TaskCard.jsx`
- **Issue**: Priority badges (`bg-red-500`, `bg-orange-500`, `bg-gray-500`) and status icons (`text-green-500`, `text-yellow-500`) use ad-hoc Tailwind color classes. While functional, these colors are not defined as part of the `DESIGN TOKENS`. This can lead to inconsistency if the color palette needs to be updated globally.
- **Issue**: The `TaskCard` component uses `<Card>` from shadcn/ui. However, the `card` design token (`bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl shadow-xl p-6`) is not explicitly applied to the `Card` component in the provided snippet. It's crucial that the `Card` component actually receives these styles to ensure visual consistency across the application.

## Positive Findings:

- **Component Usage**: Excellent adherence to using shadcn/ui components (`Card`, `Badge`, `Button`, `Avatar`, `Progress`) instead of raw HTML elements in `TaskCard.jsx`.
- **Icon Usage**: Consistent and correct use of `lucide-react` for all icons (`Calendar`, `User`, `Tag`, `Flag`, `Trash2`, `Edit`, `Clock`, `CheckCircle`, `XCircle`, `AlertCircle`), avoiding emojis.
- **Code Structure**: The `TaskCard.jsx` component is well-structured, readable, and handles conditional rendering for priority and status effectively.
- **Overall Vibe**: The intention to create a dark, modern gradient aesthetic is clear and largely successful, despite the specific gradient usage issues.

## Recommendations:

1.  **Refine Gradient Usage (DESIGN TOKENS)**:
    *   **For `pageBg`**: Replace the full-viewport gradient with a solid dark background (e.g., `bg-slate-950` or `bg-purple-950`) and apply gradients more strategically as accents. For example, a subtle gradient on a header, a specific section, or as a background for a modal, ensuring it stays below the 20% viewport threshold.
    *   **For `primaryButton`**: Experiment with more unique gradient color combinations that align with the 'modern_gradient' vibe but avoid the generic purple-pink. Consider gradients within a single hue range (e.g., `from-purple-700 to-purple-500`) or more sophisticated combinations like `from-indigo-600 to-purple-500`.

2.  **Specify Transitions (DESIGN TOKENS)**:
    *   **For `primaryButton` and `secondaryButton`**: Change `transition-all` to specific properties. For instance, `transition-[background-color,transform,box-shadow]` for buttons, as these are the most common properties that change on hover.

3.  **Enhance Design Token Compliance (TaskCard.jsx & DESIGN TOKENS)**:
    *   **For `TaskCard.jsx`**: Ensure the `Card` component explicitly receives the `card` design token classes. This can be done by passing `className={classes.card}` if `classes` are imported from the design tokens, or by configuring the shadcn/ui `Card` component to use these styles by default.
    *   **For `TaskCard.jsx`**: Introduce new design tokens for functional colors (e.g., `color-priority-high`, `color-priority-medium`, `color-priority-low`, `color-status-done`, `color-status-in-progress`) in `DESIGN TOKENS`. Then, update the `getPriorityBadge` and `getStatusIcon` functions to use these tokens instead of ad-hoc Tailwind classes like `bg-red-500` or `text-green-500`. This will centralize color management and improve consistency.