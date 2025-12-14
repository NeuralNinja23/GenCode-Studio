// Auto-generated from architecture.md UI Tokens
import tokensJson from "./tokens.json";

export const tokens = tokensJson as {
  vibe: string;
  classes: {
    pageBg: string;
    card: string;
    primaryButton: string;
    secondaryButton?: string;
    mutedText?: string;
    [key: string]: string | undefined;
  };
};

export const ui = {
  pageRoot: tokens.classes.pageBg,
  card: tokens.classes.card,
  primaryButton: tokens.classes.primaryButton,
  secondaryButton: tokens.classes.secondaryButton ?? tokens.classes.primaryButton,
  mutedText: tokens.classes.mutedText ?? "",
};
