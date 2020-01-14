// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Authorization Rule", {
	refresh: function(frm) {
		frm.events.set_master_type(frm);
	},
	set_master_type: function(frm) {
		if(frm.doc.based_on==="Customerwise Discount") {
			unhide_field("master_name");
			frm.set_value("customer_or_item", "Customer");
		} else if(frm.doc.based_on==="Itemwise Discount") {
			unhide_field("master_name");
			frm.set_value("customer_or_item", "Item");
		} else {
			frm.set_value("customer_or_item", "");
			frm.set_value("master_name", "");
			hide_field("master_name");
		}
	},
	based_on: function(frm) {
		frm.events.set_master_type(frm);
		if (frm.doc.based_on === 'Not Applicable') {
			frm.set_value("value", 0);
			hide_field('value');
		} else {
			unhide_field('value');
		}
	},
	transaction: function(frm) {
		if (frm.doc.transaction == 'Appraisal') {
			frm.set_value("based_on", "Not Applicable");
			frm.set_value("master_name", "");
			frm.set_value("system_role", "");
			frm.set_value("system_user", "");
			frm.set_value("value", 0);
			hide_field(['based_on', 'system_role', 'system_user', 'value']);
			unhide_field(['to_emp','to_designation']);
		}
		else {
			unhide_field(['system_role', 'system_user','value', 'based_on']);
			hide_field(['to_emp','to_designation']);
		}
	}
})


// Settings Module
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if (doc.based_on == 'Not Applicable')
		hide_field('value');
	else
		unhide_field('value');

	if (doc.transaction == 'Appraisal') {
		hide_field(['system_role', 'system_user']);
		unhide_field(['to_emp','to_designation']);

		if (doc.transaction == 'Appraisal')
			hide_field('value');
		else
			unhide_field('value');
	}
	else {
		unhide_field(['system_role', 'system_user','value']);
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
