import { createApp } from 'vue';
import QuarantineStation from './QuarantineStation.vue';

function setup_quarantine_station(wrapper) {
    const app = createApp(QuarantineStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_quarantine_station = setup_quarantine_station;
export default setup_quarantine_station;
