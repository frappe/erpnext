// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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
		cur_frm.add_custom_button(__("Gantt Chart"), function() {
			frappe.route_options = {"project": doc.name, "start": doc.project_start_date, "end": doc.completion_date};
			frappe.set_route("Gantt", "Task");
		}, "icon-tasks", true);
		cur_frm.add_custom_button(__("Tasks"), function() {
			frappe.route_options = {"project": doc.name}
			frappe.set_route("List", "Task");
		}, "icon-list", true);
	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.customer_query"
	}
}
