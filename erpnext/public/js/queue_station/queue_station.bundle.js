import { createApp } from 'vue';
import QueueStation from './QueueStation.vue';

function setup_queue_station(wrapper, station_name) {
	const app = createApp(QueueStation);
	window.station_name = station_name;
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_queue_station = setup_queue_station;
export default setup_queue_station;
