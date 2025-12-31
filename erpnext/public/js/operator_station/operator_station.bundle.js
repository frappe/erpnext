import { createApp } from 'vue';
import OperatorStation from './OperatorStation.vue';

function setup_operator_station(wrapper) {
    const app = createApp(OperatorStation);
    app.config.globalProperties.__ = window.__;  // reuse frappe's __
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_operator_station = setup_operator_station;
export default setup_operator_station;
