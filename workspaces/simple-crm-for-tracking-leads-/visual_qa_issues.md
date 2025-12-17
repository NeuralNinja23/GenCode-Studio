# Visual QA Issues

Reviewed by Marcus (UI Critic)

## Issues Found:

-   **Issue 1: Incomplete Design Token Application for Page Background**
    -   **File**: `App.jsx` (and potentially `Layout.jsx`)
    -   **Problem**: The `pageBg` design token (`min-h-screen bg-white text-slate-900`) is defined in `DESIGN TOKENS` but is not applied to the main application wrapper in `App.jsx`. The current `div` uses `className="App"` which does not leverage the defined token for the overall page background and text color.
    -   **Why it's an issue**: Inconsistent application of design tokens can lead to visual discrepancies and makes global style changes harder. The `minimal_light` vibe relies on this base styling.
    -   **How to fix**: Ensure the `pageBg` token is applied to the top-level layout component (e.g., `Layout.jsx` or the main `div` in `App.jsx`).
    -   **Example Fix (if applied in App.jsx)**:
        ```diff
        --- a/App.jsx
        +++ b/App.jsx
        import React from 'react';
        import Home from './pages/Home';
        import { ui } from './design/theme'; // Assuming ui is imported or passed down

        function App() {
          return (
        -    <div className="App">
        +    <div className={`${ui.pageBg}`}>
               <Home />
             </div>
           );
        }
        ```

-   **Issue 2: Generic Transition Property in Design Tokens**
    -   **File**: `DESIGN TOKENS` (specifically `primaryButton` and `secondaryButton` classes)
    -   **Problem**: The `primaryButton` and `secondaryButton` design tokens use `transition-all`. The review guidelines explicitly state: "Avoid 'transition: all' (use specific properties)".
    -   **Why it's an issue**: Using `transition-all` can be less performant as it forces the browser to track changes on all animatable properties, even those not intended for animation. It also offers less control over specific animation timings.
    -   **How to fix**: Replace `transition-all` with specific transition properties relevant to the animation (e.g., `transition-colors`, `transition-transform`, or a combination like `transition-[colors,transform]`).
    -   **Example Fix (in DESIGN TOKENS)**:
        ```diff
        --- a/DESIGN TOKENS
        +++ b/DESIGN TOKENS
        {
          "vibe": "minimal_light",
          "classes": {
            "pageBg": "min-h-screen bg-white text-slate-900",
            "card": "bg-gray-50 border border-gray-200 rounded-xl shadow-sm p-6",
        -    "primaryButton": "bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-2 rounded-lg transition-all hover:scale-105",
        +    "primaryButton": "bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-2 rounded-lg transition-[colors,transform] duration-200 hover:scale-105",
        -    "secondaryButton": "border border-gray-300 hover:bg-gray-100 text-slate-700 px-4 py-2 rounded-lg transition-all",
        +    "secondaryButton": "border border-gray-300 hover:bg-gray-100 text-slate-700 px-4 py-2 rounded-lg transition-colors duration-200",
            "mutedText": "text-gray-500 text-sm"
          }
        }
        ```

## Positive Findings:

-   **Excellent Component Usage**: `LeadCard.jsx` correctly utilizes shadcn/ui components (`Card`, `Button`, `Badge`, etc.) ensuring consistency and adherence to the design system.
-   **Correct Iconography**: All icons in `LeadCard.jsx` are sourced from `lucide-react`, avoiding emojis and maintaining a professional, consistent look.
-   **Design Token Adherence (Card)**: The `LeadCard.jsx` correctly applies the `ui.card` design token, ensuring cards have the intended `minimal_light` styling, including appropriate padding (`p-6`).
-   **Vibe Consistency**: The color palette and general styling defined in the design tokens (white/gray backgrounds, subtle borders, blue accents) perfectly match the `minimal_light` UI vibe.
-   **Clear Status Indication**: The `getStatusIcon` and `getStatusVariant` functions in `LeadCard.jsx` provide clear visual feedback for lead statuses, enhancing usability.

## Recommendations:

-   **Global Layout Styling**: Ensure the `pageBg` design token is consistently applied to the main layout wrapper (e.g., in `Layout.jsx` or the root `div` of `App.jsx`) to establish the base `minimal_light` styling across the application.
-   **Refine Button Transitions**: Update the `primaryButton` and `secondaryButton` design tokens to use specific transition properties (e.g., `transition-[colors,transform] duration-200`) instead of `transition-all` for better performance and control.
-   **Dashboard Content**: While not explicitly shown, ensure the `Home` (Dashboard) page, when implemented, contains meaningful `StatsCard`s and `RecentLeadsTable` as outlined in `ARCHITECTURE.MD`, rather than placeholder content.