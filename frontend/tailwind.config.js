/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 报纸风格色彩系统
        ink: {
          DEFAULT: '#1a1a2e',
          light: '#4a4a6a',
        },
        gold: {
          DEFAULT: '#c9a84c',
          light: '#f0e6c8',
        },
        paper: {
          DEFAULT: '#faf8f4',
          dark: '#f0ede6',
        },
        red: {
          DEFAULT: '#c23c2e',
        },
        rule: '#e0ddd6',
        // 暗色模式专用色
        'night': {
          DEFAULT: '#0d1117',
          card: '#161b22',
          border: '#30363d',
          muted: '#8b949e',
        },
        // 保留原有 primary 色系用于兼容
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'serif'],
        sans: ['DM Sans', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
      },
      boxShadow: {
        'warm': '0 2px 8px rgba(26, 26, 46, 0.08)',
        'warm-lg': '0 4px 16px rgba(26, 26, 46, 0.12)',
        'warm-xl': '0 8px 32px rgba(26, 26, 46, 0.16)',
        'night': '0 2px 8px rgba(0, 0, 0, 0.3)',
        'night-lg': '0 4px 16px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
}
