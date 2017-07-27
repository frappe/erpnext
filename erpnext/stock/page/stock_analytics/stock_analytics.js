// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['stock-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Analytics'),
		single_column: true
	});
	
	frappe.require(["assets/erpnext/js/stock_grid_report.js",
		"assets/erpnext/js/stock_analytics.js"], function() {
		new erpnext.StockAnalytics(wrapper);
		frappe.breadcrumbs.add("Stock")
	});
};
