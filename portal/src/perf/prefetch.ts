export function prefetchModule(importer: () => Promise<unknown>) {
  let started = false;
  return () => {
    if (started) return;
    started = true;
    void importer();
  };
}

export function attachPrefetch(selector: string, importer: () => Promise<unknown>) {
  const trigger = prefetchModule(importer);
  const elements = Array.from(document.querySelectorAll<HTMLElement>(selector));
  elements.forEach((el) => {
    el.addEventListener('mouseenter', trigger, { passive: true });
    el.addEventListener('focus', trigger, { passive: true });
  });
}
