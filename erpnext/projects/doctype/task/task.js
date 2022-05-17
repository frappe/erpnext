// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Task", {
	setup: function (frm) {
		frm.custom_make_buttons = {
			'Task': 'Create Child Task',
		};

		frm.make_methods = {
			'Timesheet': () => frappe.model.open_mapped_doc({
				method: 'erpnext.projects.doctype.task.task.make_timesheet',
				frm: frm
			})
		}
	},

	onload: function (frm) {
		frm.set_query("task", "depends_on", function () {
			let filters = {
				name: ["!=", frm.doc.name]
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			};
		});

		frm.set_query("parent_task", function() {
			var filters = {};

			if (frm.doc.project) {
				filters.project = frm.doc.project
			} else if (frm.doc.issue) {
				filters.issue = frm.doc.issue
			}
			filters['is_group'] = 1;

			return {
				filters: filters
			};
		});
	},

	refresh: function (frm) {
		erpnext.hide_company();

		if (frm.doc.is_group) {
			frm.add_custom_button(__('Children Task List'), () => frm.events.view_child_task(frm));
			frm.add_custom_button(__('Create Child Task'), () => frm.events.create_child_task(frm));
		}
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

	validate: function (frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project",
			frm.doc.project);
	},

	view_child_task: function (frm) {
		frappe.set_route('List', 'Task', 'List', {
			parent_task: frm.doc.name
		});
	},

	create_child_task: function (frm) {
		frappe.new_doc("Task", {
			parent_task: frm.doc.name,
			project: frm.doc.project,
			issue: frm.doc.issue,
		});
	},
});
