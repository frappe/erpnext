frappe.pages['operator-station'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Operator Station',
		single_column: true
	});

    if (frappe.boot.developer_mode) {
        frappe.hot_update ??= [];
        frappe.hot_update.push(() => load_vue(wrapper));
    }
};

frappe.pages['operator-station'].on_page_show = (wrapper) => load_vue(wrapper);

async function load_vue(wrapper) {
    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();
    await frappe.require('operator_station.bundle.js');
    frappe.operator_station_app = frappe.ui.setup_operator_station($parent);
}
