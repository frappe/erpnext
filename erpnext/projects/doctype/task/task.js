// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

cur_frm.add_fetch("project", "company", "company");

erpnext.projects.Task = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.project.get_query = function() {
			return {
				query: "erpnext.projects.doctype.task.task.get_project"
			}
		};
	},

	project: function() {
		if(this.frm.doc.project) {
			return get_server_fields('get_project_details', '','', this.frm.doc, this.frm.doc.doctype, 
				this.frm.doc.name, 1);
		}
	},

	validate: function() {
		this.frm.doc.project && frappe.model.remove_from_locals("Project",
			this.frm.doc.project);
	},
	
	refresh: function(doc) {
		if(!doc.__islocal) {
			cur_frm.add_custom_button(__("Time Logs"), function() {
				frappe.route_options = {"project": doc.project, "task": doc.name}
				frappe.set_route("List", "Time Log");
			}, "icon-list", true);
			cur_frm.add_custom_button(__("Expense Claims"), function() {
				frappe.route_options = {"project": doc.project, "task": doc.name}
				frappe.set_route("List", "Expense Claim");
			}, "icon-list", true);
		}
	}
});

cur_frm.add_fetch('task', 'subject', 'subject');

cur_frm.cscript = new erpnext.projects.Task({frm: cur_frm});

