// frontend/src/utils/debounce.ts
export function debounce<T extends (...args: any[]) => void>(fn: T, wait = 300) {
  let timer: number | undefined;
  return (...args: Parameters<T>) => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
}
