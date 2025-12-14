# Visual QA Issues

Reviewed by Marcus (UI Critic)

## Issues Found:

### 1. Vibe Mismatch & Design Token Non-Compliance (Critical)

**Issue**: The application is not consistently applying the `dark_hacker` UI vibe and the defined design tokens. Instead, it relies heavily on shadcn/ui's default `bg-background`, `text-foreground`, `bg-card`, `border-border`, and `text-muted-foreground` classes, which do not align with the specific color palette, gradients, and accent details outlined in the `DESIGN TOKENS`.

*   **File**: `App.jsx`
    *   **Line**: 7 (`<div className="min-h-screen bg-background text-foreground">`)
    *   **Problem**: The root `div` uses generic `bg-background text-foreground`. The `pageBg` design token specifies `bg-gradient-to-br from-gray-950 to-black text-gray-50 min-h-screen` for the overall page background.
    *   **Recommendation**: Replace `bg-background text-foreground` with the `pageBg` token's classes to establish the correct dark gradient background and text color.

*   **File**: `App.jsx`
    *   **Line**: 8 (`<header className="border-b border-border p-4 flex justify-between items-center bg-card shadow-sm">`)
    *   **Problem**: The header uses `bg-card border-border shadow-sm`. While `bg-card` is dark, it lacks the specific `dark_hacker` aesthetic (e.g., purple border/shadow) defined in the `card` token. The `card` token is for individual cards, but the header's styling should still be consistent with the overall theme's dark, accented feel.
    *   **Recommendation**: Adjust the header's background and border to align with the `dark_hacker` vibe. Consider using `bg-gray-900` or `bg-gray-950` for the background and a subtle `border-purple-800/50` or `shadow-purple-900/20` to introduce the theme's accent, similar to the `card` token.

*   **File**: `App.jsx`
    *   **Line**: 14, 18 (`<Button variant="ghost" ...>`) 
    *   **Problem**: Navigation buttons use `variant="ghost"`. The design tokens provide `primaryButton` and `secondaryButton` classes with specific backgrounds, borders, and hover effects (`bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700` for `secondaryButton`). Ghost buttons are too subtle for the intended `dark_hacker` aesthetic.
    *   **Recommendation**: Replace `variant="ghost"` with a custom class that applies the `secondaryButton` token's styles, or configure shadcn's `ghost` variant in `tailwind.config.js` to match the `secondaryButton` token.

*   **File**: `NoteCard.jsx`
    *   **Line**: 27 (`<Card className="bg-card border-border shadow-md hover:shadow-lg transition-shadow duration-200 ease-in-out flex flex-col">`)
    *   **Problem**: The `Card` component uses `bg-card border-border shadow-md hover:shadow-lg`. The `card` design token specifies `bg-gray-900 border border-purple-800/50 rounded-lg shadow-lg shadow-purple-900/20 hover:border-purple-600 transition-all duration-200 ease-in-out`.
    *   **Recommendation**: Replace the existing `Card` classes with the full `card` design token classes to ensure the correct background, border, shadow, and hover effects.

*   **File**: `NoteCard.jsx`
    *   **Line**: 33 (`<p className="text-muted-foreground text-sm line-clamp-3">{note.content}</p>`)
    *   **Problem**: The note content uses `text-muted-foreground`. The `mutedText` design token specifies `text-gray-500`.
    *   **Recommendation**: Replace `text-muted-foreground` with `text-gray-500` to comply with the `mutedText` token.

### 2. Incomplete Transitions & Animations

**Issue**: While some transitions are present, they do not fully implement the properties specified in the design tokens.

*   **File**: `NoteCard.jsx`
    *   **Line**: 27 (`<Card className="... transition-shadow duration-200 ease-in-out">`)
    *   **Problem**: The `Card` only transitions `shadow`. The `card` design token specifies `transition-all duration-200 ease-in-out` and includes a `hover:border-purple-600` effect.
    *   **Recommendation**: Change `transition-shadow` to `transition-all` and ensure the `hover:border-purple-600` class is applied to the card to match the token's full interactive effect.

### 3. Incomplete Code Sample (Minor)

**Issue**: The `NoteCard.jsx` code sample is truncated, preventing a full review of the action buttons (Edit, Delete).

*   **File**: `NoteCard.jsx`
    *   **Line**: 34 (`<div clas`)
    *   **Problem**: The code ends abruptly, not showing the implementation of the edit and delete buttons, which are crucial for `NoteCard` functionality and token compliance.
    *   **Recommendation**: Complete the `NoteCard.jsx` implementation, ensuring that the Edit and Delete buttons utilize the `primaryButton` or `secondaryButton` design tokens as appropriate.

## Positive Findings:

*   **Icon Usage**: Excellent use of `lucide-react` for all icons (`NotebookPen`, `HomeIcon`, `Edit`, `Trash2`, `CheckCircle`, `Clock`), adhering strictly to the guidelines.
*   **Component Usage**: Correctly utilizes shadcn/ui components like `Card`, `CardHeader`, `CardTitle`, `CardContent`, `Button`, and `Badge`, demonstrating good component-based development.
*   **Layout & Spacing**: The general `p-4` and `gap-4` spacing in `App.jsx` and `pb-2`, `space-y-4` in `NoteCard.jsx` appear reasonable and not overtly cramped, providing adequate whitespace.
*   **Structure**: The overall component hierarchy and routing setup in `App.jsx` are clear and well-structured.

## Recommendations:

1.  **Prioritize Design Token Integration**: The most critical step is to integrate the provided `DESIGN TOKENS` directly into the component classes. This might involve creating custom utility classes or configuring `tailwind.config.js` to override shadcn defaults to match the `dark_hacker` theme's specific colors and styles (e.g., `primary`, `secondary`, `background`, `card`, `border`, `muted-foreground`).
2.  **Complete `NoteCard.jsx`**: Implement the Edit and Delete actions within `NoteCard.jsx`, ensuring they use the `primaryButton` or `secondaryButton` design tokens for consistent styling and interactive feedback.
3.  **Content for Home Page**: While not directly in the provided code, ensure the `Home.jsx` component (or `/` route) provides meaningful content beyond a simple 