import { buildIslands } from "@framework/ui/vite/island";

await buildIslands({
	app: "erpnext",
	root: import.meta.dirname,
	entries: {
		"erpnext.project_costing": "src/project_costing/index.js",
		"erpnext.project_overview": "src/project_overview/index.js",
	},
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
