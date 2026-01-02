frappe.pages['operator-station'].on_page_load = function(wrapper) {
    let route = frappe.get_route?.() || {};
    console.log(route);
    let station = route[2] || 'operator'
    let job_card = route[3] || null;
    const station_map = {
        'distribution': { title: 'Distribution Station', process: 'distribution' },
        'pressing': { title: 'Pressing Station', process: 'pressing'},
        'callibration': { title: 'Callibration Station', process: 'callibration' },
        'operator': { title: 'Operator Station', process: 'operator'}
    }
    let config = station_map[station] || station_map['operator']
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: config.title,
		single_column: true
	});

    if (frappe.boot.developer_mode) {
        frappe.hot_update ??= [];
        frappe.hot_update.push(() => load_vue(wrapper, { config, page, job_card }));
    }
    load_vue(wrapper, { config, page, job_card });
};

frappe.pages['operator-station'].on_page_show = (wrapper) => {
    let route = frappe.get_route?.() || {};
    let station = route[2] || 'operator'
    let job_card = route[3] || null;
    const station_map = {
        'distribution': { title: 'Distribution Station', process: 'distribution' },
        'pressing': { title: 'Pressing Station', process: 'pressing'},
        'callibration': { title: 'Callibration Station', process: 'callibration' },
        'operator': { title: 'Operator Station', process: 'operator'}
    }
    let config = station_map[station] || station_map['operator']
    let page = $(wrapper).closest('.layout-wrapper').data('page');  

    load_vue(wrapper, { config, page, job_card });
};

async function load_vue(wrapper, params) {
    const { config, page, job_card } = params;

    if (page && config?.title) {
        page.set_title(config.title);  
    }
    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();
    await frappe.require('operator_station.bundle.js');
    frappe.operator_station_app = frappe.ui.setup_operator_station($parent, params.config.process, job_card);
}