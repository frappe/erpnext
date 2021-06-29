frappe.pages['organizational-chart'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Organizational Chart'),
		single_column: true
	});

	$(wrapper).bind('show', () => {
		frappe.require('/assets/js/hierarchy-chart.min.js', () => {
			let organizational_chart = undefined;
			if (frappe.is_mobile()) {
				organizational_chart = new erpnext.HierarchyChartMobile(wrapper);
			} else {
				organizational_chart = new erpnext.HierarchyChart(wrapper);
			}
			organizational_chart.show();
		});
	});
};