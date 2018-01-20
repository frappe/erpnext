// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipping Plan', {
	refresh: function(frm) {

	}
});

cur_frm.fields_dict['delivery_note'].get_query = function(doc) {
	return{
		filters:{ 'docstatus': 0}
	};
};