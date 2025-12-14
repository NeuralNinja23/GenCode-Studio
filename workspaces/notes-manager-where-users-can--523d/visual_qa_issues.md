# Visual QA Issues

Reviewed by Marcus (UI Critic)

## Issues Found:

### 1. Design Token Compliance - Page Background (`App.jsx`)
- **File**: `App.jsx`
- **Line**: 6
- **Problem**: The root `div` uses `className="min-h-screen bg-background text-foreground"`. While `bg-background` and `text-foreground` are shadcn/ui defaults for dark mode, they do not directly use the specific `pageBg` design token defined as `bg-slate-950 text-slate-100`.
- **Impact**: This creates a slight inconsistency with the explicitly defined `dark_hacker` vibe's base colors, potentially leading to a different shade of dark background than intended.
- **Recommendation**: Replace `bg-background text-foreground` with the `pageBg` token's classes.
  ```diff
  - <div className="min-h-screen bg-background text-foreground">
  + <div className="min-h-screen bg-slate-950 text-slate-100">
  ```

### 2. Design Token Compliance - Note Card Styling (`NoteCard.jsx`)
- **File**: `NoteCard.jsx`
- **Line**: 23
- **Problem**: The `Card` component uses `className="bg-card border border-border shadow-lg flex flex-col h-full"`. This uses shadcn/ui's default card styling, but it does not apply the specific `card` design token defined as `bg-slate-900/60 border border-slate-800 rounded-2xl shadow-lg p-6`.
- **Impact**: The card's background color (`bg-slate-900/60`), border color (`border-slate-800`), border radius (`rounded-2xl`), and crucial internal padding (`p-6`) are not being applied from the design system. This will result in a different visual appearance and potentially cramped spacing within the card.
- **Recommendation**: Update the `Card` component's `className` to use the design token's properties.
  ```diff
  - <Card className="bg-card border border-border shadow-lg flex flex-col h-full">
  + <Card className="bg-slate-900/60 border border-slate-800 rounded-2xl shadow-lg p-6 flex flex-col h-full">
  ```

### 3. Design Token Compliance - Button Transitions (`NoteCard.jsx`)
- **File**: `NoteCard.jsx`
- **Lines**: 39, 40 (for Delete and Edit buttons)
- **Problem**: The `primaryButton` and `secondaryButton` design tokens explicitly include `transition-all hover:scale-105` and `transition-all` respectively. The `Button` components for 'Delete' and 'Edit' in `NoteCard` rely on shadcn/ui's default button styles and transitions, which may not match the specified `hover:scale-105` or other custom transition properties from the tokens.
- **Impact**: Inconsistent micro-animations and hover feedback across interactive elements, deviating from the intended `dark_hacker` interaction feel.
- **Recommendation**: For the 'Edit' button, consider applying the `secondaryButton` token's classes to ensure consistent styling and hover effects. For the 'Delete' button, while `variant="destructive"` is appropriate, ensure its hover effect aligns with the general interaction principles (e.g., a subtle scale or color shift).
  ```diff
  - <Button variant="outline" size="sm" onClick={() => onEdit(note.id)} disabled={loading}>
  + <Button className="border border-slate-700 hover:bg-slate-800 text-slate-100 px-4 py-2 rounded-lg transition-all" size="sm" onClick={() => onEdit(note.id)} disabled={loading}>
  ```
  (Note: The `px-4 py-2 rounded-lg` might be redundant if shadcn's `size="sm"` already handles it, but `border border-slate-700 hover:bg-slate-800 text-slate-100 transition-all` are key.)

## Positive Findings:

*   **Component Usage**: Excellent adherence to using shadcn/ui components (`Card`, `Button`, `Badge`) instead of raw HTML elements, ensuring a consistent UI foundation.
*   **Icon Usage**: Correct and consistent use of `lucide-react` for all icons (`Trash2`, `Edit`, `CheckCircle`, etc.), aligning with best practices and the `dark_hacker` aesthetic.
*   **Vibe Alignment**: The `DESIGN TOKENS` themselves are well-crafted and strongly align with the `dark_hacker` vibe, using appropriate dark backgrounds, muted text, and a vibrant emerald accent color.
*   **Content Handling**: The `NoteCard` includes practical UX features like content truncation, which is good for readability in a grid layout.
*   **Status Badges**: The implementation of status badges with relevant icons and colors is a thoughtful addition for managing notes effectively.

## Recommendations:

1.  **Strict Design Token Application**: Prioritize the direct application of defined design token classes (e.g., `pageBg`, `card`, `primaryButton`, `secondaryButton`) to ensure the UI precisely matches the design system's specifications. Avoid relying solely on shadcn/ui defaults when a specific token exists.
2.  **Centralized Styling for Shadcn Components**: For shadcn/ui components that have corresponding design tokens (like `Button` or `Card`), consider creating wrapper components or using a utility function to apply the token classes consistently, rather than manually adding them to each instance. This improves maintainability.
3.  **Review Spacing**: After applying the `p-6` from the `card` token, re-evaluate the internal spacing of `CardHeader`, `CardContent`, and `CardFooter` to ensure a balanced and un-cramped layout, especially given the `dark_hacker` vibe often benefits from ample whitespace.