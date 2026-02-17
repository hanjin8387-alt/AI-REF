/**
 * PROMETHEUS Design System Colors
 * Primary: #00D084 (Fresh Green)
 */

const primary = '#00D084';
const primaryDark = '#00B571';
const primaryLight = '#4AEDB5';

export default {
  primary,
  primaryDark,
  primaryLight,

  // Status Colors
  warning: '#FFB800',
  danger: '#FF4757',
  success: '#00D084',
  info: '#3498DB',

  // Neutral Colors
  white: '#FFFFFF',
  black: '#000000',
  gray50: '#F9FAFB',
  gray100: '#F3F4F6',
  gray200: '#E5E7EB',
  gray300: '#D1D5DB',
  gray400: '#9CA3AF',
  gray500: '#6B7280',
  gray600: '#4B5563',
  gray700: '#374151',
  gray800: '#1F2937',
  gray900: '#111827',

  // Glassmorphism
  glass: 'rgba(255, 255, 255, 0.1)',
  glassBorder: 'rgba(255, 255, 255, 0.2)',

  // Theme-specific
  light: {
    text: '#132018',
    textSecondary: '#5E6F66',
    background: '#F5F8F7',
    surface: '#ECF3F0',
    card: '#FFFFFF',
    border: '#DDE6E1',
    tint: primary,
    tabIconDefault: '#6D7D74',
    tabIconSelected: primary,
  },
  dark: {
    text: '#F9FAFB',
    textSecondary: '#9CA3AF',
    background: '#0F172A',
    surface: '#1E293B',
    card: '#1E293B',
    border: '#334155',
    tint: primaryLight,
    tabIconDefault: '#64748B',
    tabIconSelected: primaryLight,
  },
};
