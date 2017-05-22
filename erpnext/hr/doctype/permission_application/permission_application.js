// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");
cur_frm.add_fetch('employee', 'cell_number', 'cell_number');
cur_frm.add_fetch('employee', 'department', 'department');
cur_frm.add_fetch('employee', 'designation', 'designation');

frappe.ui.form.on('Permission Application', {
	onload: function(frm) {
		frm.set_query("reports_to", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});

		frm.set_query("employee", erpnext.queries.employee);

	},
	refresh: function(frm) {
		if (frm.doc.__islocal) {
			get_employee(frm);
		}
		if( in_list(user_roles, "HR Manager") && !frm.doc.__islocal) {
			frm.set_df_property("permission_time", "read_only", !in_list(user_roles, "HR Manager"));	
			frm.set_df_property("permission_time_to", "read_only", !in_list(user_roles, "HR Manager"));	
		}
	}
	
	,
	permission_time_to: function(frm) {
		get_total(frm);
	}
	,
	permission_time: function(frm) {
		get_total(frm);
	}
	
});
var get_employee = function (frm)
{
	frappe.call({
		doc: frm.doc,
		method: "get_employee",
		callback: function(r) {
			refresh_many(['employee','employee_name']);
		}
	});
};
var get_total = function (frm)
{
	frappe.call({
		doc: frm.doc,
		method: "get_total",
		callback: function(r) {
			refresh_many(['total']);
		}
	});
};


cur_frm.cscript.employee = function(doc, cdt, cd){
	if (!doc.employee) {
		cur_frm.set_value("employee_name", "");
		
	}
	cur_frm.set_value("reports_to", "");
};

//~ cur_frm.set_query("reports_to", function() {
			//~ return {
				//~ query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				//~ filters: {
					//~ employee: cur_frm.doc.employee
				//~ }
			//~ };
		//~ });
		
//~ cur_frm.fields_dict.reports_to.get_query = function(doc,cdt,cdn) {
		//~ return{
			//~ query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				//~ filters: {
					//~ employee: cur_frm.doc.employee
				//~ }
		//~ }	
	//~ }
