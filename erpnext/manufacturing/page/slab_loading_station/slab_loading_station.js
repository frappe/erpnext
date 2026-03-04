frappe.pages['slab-loading-station'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Slab Loading Station',
		single_column: true
	});

	const refresh_page = async () => {
		if (frappe.slab_loading_station_app?._instance?.proxy) {
			document.dispatchEvent(new CustomEvent('refresh-slab-loading-station'));
		}
	};

	page.add_inner_button('<span class="fa fa-refresh"></span>', refresh_page);

    if (frappe.boot.developer_mode) {
        frappe.hot_update ??= [];
        frappe.hot_update.push(() => load_vue(wrapper));
    }
}

frappe.pages['slab-loading-station'].on_page_show = (wrapper) => load_vue(wrapper);

async function load_vue(wrapper) {
    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();
    await frappe.require('slab_loading_station.bundle.js');
    frappe.slab_loading_station_app = frappe.ui.setup_slab_loading_station($parent);
}