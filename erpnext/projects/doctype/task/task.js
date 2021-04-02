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
		frm.fields_dict['parent_task'].get_query = function () {
			return {
				filters: {
					"is_group": 1,
				}
			}
		}

		if (!frm.doc.is_group) {
			if (!frm.is_new()) {
				if (frappe.model.can_read("Timesheet")) {
					frm.add_custom_button(__("Timesheet"), () => {
						frappe.route_options = { "project": frm.doc.project, "task": frm.doc.name }
						frappe.set_route("List", "Timesheet");
					}, __("View"), true);
				}

				if (frappe.model.can_read("Expense Claim")) {
					frm.add_custom_button(__("Expense Claims"), () => {
						frappe.route_options = { "project": frm.doc.project, "task": frm.doc.name };
						frappe.set_route("List", "Expense Claim");
					}, __("View"), true);
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

	is_group: function (frm) {
		frappe.call({
			method: "erpnext.projects.doctype.task.task.check_if_child_exists",
			args: {
				name: frm.doc.name
			},
			callback: function (r) {
				if (r.message.length > 0) {
					frappe.msgprint(__(`Cannot convert it to non-group. The following child Tasks exist: ${r.message.join(", ")}.`));
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
