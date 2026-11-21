import { readFileSync } from 'node:fs';
import path from 'node:path';

const config_path = process.env.FRAPPE_BENCH_PATH ? path.join(process.env.FRAPPE_BENCH_PATH, 'sites', 'common_site_config.json') : new URL('../../../sites/common_site_config.json', import.meta.url);

const common_site_config = JSON.parse(
	readFileSync(config_path, 'utf8')
) as { webserver_port: string | number };
const { webserver_port } = common_site_config;

export default {
	'^/(app|api|assets|files|private)': {
		target: `http://127.0.0.1:${webserver_port}`,
		ws: true,
		router: function (req) {
			const site_name = req.headers?.host?.split(':')[0];
			return `http://${site_name ?? 'localhost'}:${webserver_port}`;
		}
	}
};
