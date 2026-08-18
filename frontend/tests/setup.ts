import '@testing-library/jest-dom/vitest';

// jsdom ships neither of these, and both are on the render path: the motion-preference
// hook queries matchMedia, and Leaflet asks for element sizes.
if (typeof window.matchMedia !== 'function') {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
