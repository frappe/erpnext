import { createApp } from 'vue';
import CuringStation from './CuringStation.vue';

function setup_curing_station(wrapper) {
    const app = createApp(CuringStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_curing_station = setup_curing_station;
export default setup_curing_station;
