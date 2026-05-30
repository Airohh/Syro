/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Design System - Palette moderne (style Cursor/ChatGPT)
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Domaines avec couleurs distinctes et professionnelles
        domain: {
          tech: {
            DEFAULT: '#2563eb',      // Blue 600
            light: '#dbeafe',        // Blue 100
            dark: '#1e40af',         // Blue 800
            gradient: 'from-blue-500 to-blue-600',
          },
          medical: {
            DEFAULT: '#059669',      // Emerald 600
            light: '#d1fae5',        // Emerald 100
            dark: '#065f46',         // Emerald 800
            gradient: 'from-emerald-500 to-emerald-600',
          },
          legal: {
            DEFAULT: '#7c3aed',      // Violet 600
            light: '#ede9fe',        // Violet 100
            dark: '#5b21b6',         // Violet 800
            gradient: 'from-violet-500 to-violet-600',
          },
          finance: {
            DEFAULT: '#d97706',      // Amber 600
            light: '#fef3c7',        // Amber 100
            dark: '#92400e',         // Amber 800
            gradient: 'from-amber-500 to-amber-600',
          },
          education: {
            DEFAULT: '#db2777',      // Pink 600
            light: '#fce7f3',        // Pink 100
            dark: '#9f1239',         // Pink 800
            gradient: 'from-pink-500 to-pink-600',
          },
        },
        // Neutres modernes (style Vercel)
        gray: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['0.9375rem', { lineHeight: '1.5rem' }],  // 15px base
        'lg': ['1rem', { lineHeight: '1.5rem' }],
        'xl': ['1.125rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        'sidebar': '16rem',      // 256px - sidebar fine
        'sidebar-sm': '12rem',   // 192px - sidebar compacte
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'soft': '0 1px 3px 0 rgba(0,0,0,0.4), 0 1px 2px 0 rgba(0,0,0,0.3)',
        'medium': '0 4px 12px rgba(0,0,0,0.5)',
        'large': '0 10px 40px rgba(0,0,0,0.6)',
        'glow': '0 0 20px rgba(59,130,246,0.25)',
        'glow-sm': '0 0 10px rgba(59,130,246,0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      opacity: {
        6: '0.06',
        8: '0.08',
      },
    },
  },
  safelist: [
    // Domain colors - backgrounds
    'bg-domain-tech',
    'bg-domain-medical',
    'bg-domain-legal',
    'bg-domain-finance',
    'bg-domain-education',
    'bg-domain-tech-light',
    'bg-domain-medical-light',
    'bg-domain-legal-light',
    'bg-domain-finance-light',
    'bg-domain-education-light',
    // Domain colors - text
    'text-domain-tech',
    'text-domain-medical',
    'text-domain-legal',
    'text-domain-finance',
    'text-domain-education',
    // Domain colors - borders
    'border-domain-tech',
    'border-domain-medical',
    'border-domain-legal',
    'border-domain-finance',
    'border-domain-education',
    'hover:border-domain-tech',
    'hover:border-domain-medical',
    'hover:border-domain-legal',
    'hover:border-domain-finance',
    'hover:border-domain-education',
    'hover:bg-opacity-80',
  ],
  plugins: [],
}
