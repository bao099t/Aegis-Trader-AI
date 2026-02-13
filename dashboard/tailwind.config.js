/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'cyber-black': '#0a0a0f',
                'cyber-gray': '#1c1c24',
                'neon-blue': '#00f3ff',
                'neon-pink': '#ff00ff',
                'neon-green': '#00ff41',
            },
            fontFamily: {
                'mono': ['Space Mono', 'monospace'],
            },
        },
    },
    plugins: [],
}
