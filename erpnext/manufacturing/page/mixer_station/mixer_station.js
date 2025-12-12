frappe.pages['mixer-station'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Mixer Station',
		single_column: true
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update ??= [];
		frappe.hot_update.push(() => load_vue(wrapper));
	}
};

frappe.pages['mixer-station'].on_page_show = (wrapper) => load_vue(wrapper);

async function load_vue(wrapper) {
    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();
    await frappe.require('mixer_station.bundle.js');
    frappe.mixer_station_app = frappe.ui.setup_mixer_station($parent);
}
