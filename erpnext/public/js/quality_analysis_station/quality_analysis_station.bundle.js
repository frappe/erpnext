import { createApp } from 'vue';
import QualityAnalysisStation from './QualityAnalysisStation.vue';

function setup_quality_analysis_station(wrapper) {
    const app = createApp(QualityAnalysisStation);
    app.config.globalProperties.frappe = window.frappe;
    app.config.globalProperties.__ = window.__;
    app.mount(wrapper.get(0));
    return app;
}

frappe.ui.setup_quality_analysis_station = setup_quality_analysis_station;
export default setup_quality_analysis_station;
