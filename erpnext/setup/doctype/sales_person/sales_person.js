// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Sales Person', {
	refresh: function(frm) {
		if(frm.doc.__onload && frm.doc.__onload.dashboard_info) {
			var info = frm.doc.__onload.dashboard_info;
			frm.dashboard.add_indicator(__('Total Contribution Amount: {0}',
				[format_currency(info.allocated_amount, info.currency)]), 'blue');
		}
	}
});

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root
	if(!doc.parent_sales_person) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root sales person and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select sales person
cur_frm.fields_dict['parent_sales_person'].get_query = function(doc, cdt, cdn) {
	return{
		filters: [
			['Sales Person', 'is_group', '=', 1],
			['Sales Person', 'name', '!=', doc.sales_person_name]
		]
	}
}

cur_frm.fields_dict.employee.get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.employee_query" }
}
