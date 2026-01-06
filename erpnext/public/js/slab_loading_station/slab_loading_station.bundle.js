import { createApp } from 'vue';
import SlabLoadingStation from './SlabLoadingStation.vue';

function setup_slab_loading_station(wrapper) {
    const app = createApp(SlabLoadingStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_slab_loading_station = setup_slab_loading_station;
export default setup_slab_loading_station;
