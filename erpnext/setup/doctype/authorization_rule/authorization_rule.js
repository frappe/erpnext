// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Settings Module
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if (doc.based_on == 'Grand Total' || doc.based_on == 'Average Discount' || doc.based_on == 'Not Applicable')
		hide_field('master_name');
	else
		unhide_field('master_name');

	if (doc.based_on == 'Not Applicable')
		hide_field('value');
	else
		unhide_field('value');

	if (doc.transaction == 'Appraisal') {
		hide_field(['master_name','system_role', 'system_user']);
		unhide_field(['to_emp','to_designation']);

		if (doc.transaction == 'Appraisal')
			hide_field('value');
		else
			unhide_field('value');
	}
	else {
		unhide_field(['master_name','system_role', 'system_user','value']);
		hide_field(['to_emp','to_designation']);
	}
}

cur_frm.cscript.based_on = function(doc) {
	if (doc.based_on == 'Grand Total' || doc.based_on == 'Average Discount' || doc.based_on == 'Not Applicable') {
		doc.master_name = '';
		refresh_field('master_name');
		hide_field('master_name');
	}
	else
		unhide_field('master_name');

	if (doc.based_on == 'Not Applicable') {
		doc.value =0;
		refresh_field('value');
		hide_field('value');
	}
	else
		unhide_field('value');
}

cur_frm.cscript.transaction = function(doc, cdt, cdn){
	if (doc.transaction == 'Appraisal') {
		doc.based_on == 'Not Applicable';
		doc.master_name = doc.system_role = doc.system_user = '';
		refresh_many(['master_name','system_role', 'system_user', 'based_on']);
		hide_field(['master_name','system_role', 'system_user']);
		unhide_field(['to_emp','to_designation']);
		doc.value = 0;
		refresh_many('value');
		hide_field('value');
	}
	else {
		unhide_field(['master_name','system_role', 'system_user','value']);
		hide_field(['to_emp','to_designation']);
	}

}

cur_frm.fields_dict.system_user.get_query = function(doc, cdt, cdn) {
	return { query:"frappe.core.doctype.user.user.user_query" }
}

cur_frm.fields_dict.approving_user.get_query = function(doc, cdt, cdn) {
	return { query:"frappe.core.doctype.user.user.user_query" }
}

cur_frm.fields_dict['approving_role'].get_query = cur_frm.fields_dict['system_role'].get_query;

// System Role Trigger
// -----------------------
cur_frm.fields_dict['system_role'].get_query = function(doc) {
	return {
		filters:[
			['Role', 'name', 'not in', 'Administrator, Guest, All']
		]
	}
}


// Master Name Trigger
// --------------------
cur_frm.fields_dict['master_name'].get_query = function(doc) {
	if (doc.based_on == 'Customerwise Discount')
		return {
			doctype: "Customer",
			filters:[
				['Customer', 'docstatus', '!=', 2]
			]
		}
	else if (doc.based_on == 'Itemwise Discount')
		return {
			doctype: "Item",
			query: "erpnext.controllers.queries.item_query"
		}
	else
		return {
			filters: [
				['Item', 'name', '=', 'cheating done to avoid null']
			]
		}
}

cur_frm.fields_dict.to_emp.get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.employee_query" }
}
