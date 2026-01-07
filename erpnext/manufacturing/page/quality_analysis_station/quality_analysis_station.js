frappe.pages['quality-analysis-station'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Quality Analysis Station',
		single_column: true
	});

    if (frappe.boot.developer_mode) {
        frappe.hot_update ??= [];
        frappe.hot_update.push(() => load_vue(wrapper));
    }
};

frappe.pages['quality-analysis-station'].on_page_show = (wrapper) => load_vue(wrapper);

async function load_vue(wrapper) {
    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();
    await frappe.require('quality_analysis_station.bundle.js');
    frappe.quality_analysis_station_app = frappe.ui.setup_quality_analysis_station($parent);
}