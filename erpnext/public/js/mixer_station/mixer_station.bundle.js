import { createApp } from 'vue';
import MixerStation from './MixerStation.vue';

function setup_mixer_station($parent) {
    const el = document.createElement('div');
    $parent[0].appendChild(el);

    const app = createApp(MixerStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;   // reuse Frappe's __
    app.mount(el);
    return app;
}

frappe.ui.setup_mixer_station = setup_mixer_station;
export default setup_mixer_station;