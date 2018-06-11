// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.fields_dict['default_purchase_item_price_list'].get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['enabled', '=', '1'],
			['buying', '=', '1']
		]
	}
}

cur_frm.fields_dict['default_sales_item_price_list'].get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['enabled', '=', '1'],
			['selling', '=', '1']
		]
	}
}

frappe.ui.form.on('Stock Settings', {
	refresh: function(frm) {

	}
});
