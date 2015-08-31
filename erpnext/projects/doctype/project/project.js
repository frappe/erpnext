// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Project", {
	onload: function(frm) {
		var so = frappe.meta.get_docfield("Project", "sales_order");
		so.get_route_options_for_new_doc = function(field) {
			if(frm.is_new()) return;
			return {
				"customer": frm.doc.customer,
				"project_name": frm.doc.name
			}
		}
	}
});

frappe.ui.form.on("Project Task", "edit_task", function(frm, doctype, name) {
	var doc = frappe.get_doc(doctype, name);
	if(doc.task_id) {
		frappe.set_route("Form", "Task", doc.task_id);
	} else {
		msgprint(__("Save the document first."));
	}
})

// show tasks
cur_frm.cscript.refresh = function(doc) {
	if(!doc.__islocal) {
		if(frappe.model.can_read("Task")) {
			cur_frm.add_custom_button(__("Gantt Chart"), function() {
				frappe.route_options = {"project": doc.name, "start": doc.expected_start_date, "end": doc.expected_end_date};
				frappe.set_route("Gantt", "Task");
			}, "icon-tasks", true);
			cur_frm.add_custom_button(__("Tasks"), function() {
				frappe.route_options = {"project": doc.name}
				frappe.set_route("List", "Task");
			}, "icon-list", true);
		}
		if(frappe.model.can_read("Time Log")) {
			cur_frm.add_custom_button(__("Time Logs"), function() {
				frappe.route_options = {"project": doc.name}
				frappe.set_route("List", "Time Log");
			}, "icon-list", true);
		}

		if(frappe.model.can_read("Expense Claim")) {
			cur_frm.add_custom_button(__("Expense Claims"), function() {
				frappe.route_options = {"project": doc.name}
				frappe.set_route("List", "Expense Claim");
			}, "icon-list", true);
		}
	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.customer_query"
	}
}

cur_frm.fields_dict['sales_order'].get_query = function(doc) {
	return {
		filters:{
			'project_name': doc.name
		}
	}
}
