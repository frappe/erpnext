// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

cur_frm.add_fetch("project", "company", "company");

frappe.ui.form.on("Task", {
	onload: function(frm) {
		frm.set_query("task", "depends_on", function() {
			var filters = {
				name: ["!=", frm.doc.name]
			};
			if(frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			};
		})
	},

	refresh: function(frm) {
		frm.fields_dict['parent_task'].get_query = function() {
			return {
				filters: {
					"is_group": 1,
				}
			}
		}
		if(!frm.is_group){
			var doc = frm.doc;
			if(doc.__islocal) {
				if(!frm.doc.exp_end_date) {
					frm.set_value("exp_end_date", frappe.datetime.add_days(new Date(), 7));
				}
			}

			if(!doc.__islocal) {
				if(frappe.model.can_read("Timesheet")) {
					frm.add_custom_button(__("Timesheet"), function() {
						frappe.route_options = {"project": doc.project, "task": doc.name}
						frappe.set_route("List", "Timesheet");
					}, __("View"), true);
				}
				if(frappe.model.can_read("Expense Claim")) {
					frm.add_custom_button(__("Expense Claims"), function() {
						frappe.route_options = {"project": doc.project, "task": doc.name}
						frappe.set_route("List", "Expense Claim");
					}, __("View"), true);
				}

				if(frm.perm[0].write) {
					if(frm.doc.status!=="Closed" && frm.doc.status!=="Cancelled") {
						frm.add_custom_button(__("Close"), function() {
							frm.set_value("status", "Closed");
							frm.save();
						});
					} else {
						frm.add_custom_button(__("Reopen"), function() {
							frm.set_value("status", "Open");
							frm.save();
						});
					}
				}
			}
		}
	},

	setup: function(frm) {
		frm.fields_dict.project.get_query = function() {
			return {
				query: "erpnext.projects.doctype.task.task.get_project"
			}
		};
	},

	project: function(frm) {
		if(frm.doc.project) {
			return get_server_fields('get_project_details', '','', frm.doc, frm.doc.doctype,
				frm.doc.name, 1);
		}
	},

	is_group: function(frm) {
		frappe.call({
			method:"erpnext.projects.doctype.task.task.check_if_child_exists",
			args: {
				name: frm.doc.name
			},
			callback: function(r){
				if(r.message){
					frappe.msgprint(__('Cannot convert it to non-group. Child Tasks exist.'));
					frm.reload_doc();
				}
			}
		})
	},

	validate: function(frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project",
			frm.doc.project);
	},

});

cur_frm.add_fetch('task', 'subject', 'subject');
cur_frm.add_fetch('task', 'project', 'project');
