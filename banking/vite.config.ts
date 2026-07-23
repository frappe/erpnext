import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react'
import proxyOptions from './proxyOptions';
import tailwindcss from "@tailwindcss/vite"

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [react(), tailwindcss()],
	server: {
		port: 8080,
		host: '0.0.0.0',
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	build: {
		outDir: '../erpnext/public/banking',
		emptyOutDir: true,
		target: 'es2015',
		rollupOptions: {
			output: {
				manualChunks(id) {
					if (!id.includes('node_modules')) {
						return
					}
					if (id.includes('react-dom') || id.includes('/react/')) {
						return 'vendor-react'
					}
					if (id.includes('frappe-react-sdk')) {
						return 'vendor-frappe'
					}
					if (id.includes('@tanstack')) {
						return 'vendor-tanstack'
					}
					if (id.includes('fuse.js')) {
						return 'vendor-fuse'
					}
					if (id.includes('radix-ui') || id.includes('@radix-ui')) {
						return 'vendor-radix'
					}
					if (id.includes('jotai')) {
						return 'vendor-jotai'
					}
					if (id.includes('lucide-react')) {
						return 'vendor-lucide'
					}
				},
			},
		},
	},
});
