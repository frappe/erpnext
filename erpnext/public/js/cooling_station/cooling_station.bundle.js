import { createApp } from 'vue';
import CoolingStation from './CoolingStation.vue';

function setup_cooling_station($parent) {
    const el = document.createElement('div');
    $parent[0].appendChild(el);

    const app = createApp(CoolingStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;   // reuse Frappe's __
    app.mount(el);
    return app;
}

frappe.ui.setup_cooling_station = setup_cooling_station;
export default setup_cooling_station;