import { createApp } from 'vue';
import OvenStation from './OvenStation.vue';

function setup_oven_station(wrapper) {
    const app = createApp(OvenStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_oven_station = setup_oven_station;
export default setup_oven_station;
