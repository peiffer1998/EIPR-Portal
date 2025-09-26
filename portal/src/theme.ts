export const palette = {
  primary: '#1F4E78',
  primaryDark: '#16385A',
  accent: '#FF8A3D',
  accentMuted: '#FFC29E',
  success: '#2CA58D',
  warning: '#F3A712',
  danger: '#D64550',
  slate: '#1B2432',
  fog: '#F5F7FA',
};

export const radii = {
  xs: '4px',
  sm: '6px',
  md: '10px',
  lg: '16px',
  pill: '9999px',
};

export const spacing = {
  gutter: '1.5rem',
  block: '2.5rem',
  card: '1.25rem',
};

export const typography = {
  heading: {
    fontFamily: '"Poppins", system-ui, sans-serif',
    weights: {
      regular: 500,
      bold: 700,
    },
  },
  body: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    weights: {
      regular: 400,
      medium: 500,
    },
  },
  scale: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.5rem',
    display: '2.75rem',
  },
};

export const shadows = {
  card: '0 10px 30px rgba(18, 38, 67, 0.08)',
  popover: '0 20px 40px rgba(10, 24, 43, 0.12)',
};

export const theme = {
  palette,
  radii,
  spacing,
  typography,
  shadows,
};

export type Theme = typeof theme;
