// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.pages['stock-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Analytics'),
		single_column: true
	});

	new erpnext.StockAnalytics(wrapper);


	frappe.add_breadcrumbs("Stock")

};

frappe.assets.views["Report"]();
frappe.require("assets/erpnext/js/stock_analytics.js");
