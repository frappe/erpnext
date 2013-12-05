// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


wn.pages['stock-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Stock Analytics'),
		single_column: true
	});

	new erpnext.StockAnalytics(wrapper);


	wrapper.appframe.add_module_icon("Stock")
	
}

wn.require("app/js/stock_analytics.js");