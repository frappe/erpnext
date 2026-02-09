import { createApp } from 'vue';
import CoolingStation from './CoolingStation.vue';

function setup_cooling_station(wrapper) {
    const app = createApp(CoolingStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_cooling_station = setup_cooling_station;
export default setup_cooling_station;
