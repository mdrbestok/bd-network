/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Custom colors for node types
        company: {
          DEFAULT: '#3b82f6',
          light: '#93c5fd',
        },
        asset: {
          DEFAULT: '#10b981',
          light: '#6ee7b7',
        },
        trial: {
          DEFAULT: '#f59e0b',
          light: '#fcd34d',
        },
        deal: {
          DEFAULT: '#8b5cf6',
          light: '#c4b5fd',
        },
      },
    },
  },
  plugins: [],
};
