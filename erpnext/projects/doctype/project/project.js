// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.ui.form.on("Project", {
	setup: function (frm) {
		frm.set_indicator_formatter('title',
			function (doc) {
				let indicator = 'orange';
				if (doc.status == 'Overdue') {
					indicator = 'red';
				} else if (doc.status == 'Cancelled') {
					indicator = 'dark grey';
				} else if (doc.status == 'Closed') {
					indicator = 'green';
				}
				return indicator;
			}
		);
	},

	onload: function (frm) {
		var so = frappe.meta.get_docfield("Project", "sales_order");
		so.get_route_options_for_new_doc = function (field) {
			if (frm.is_new()) return;
			return {
				"customer": frm.doc.customer,
				"project_name": frm.doc.name
			}
		}

		frm.set_query('customer', 'erpnext.controllers.queries.customer_query');

		frm.set_query("user", "users", function () {
			return {
				query: "erpnext.projects.doctype.project.project.get_users_for_project"
			}
		});

		// sales order
		frm.set_query('sales_order', function () {
			var filters = {
				'project': ["in", frm.doc.__islocal ? [""] : [frm.doc.name, ""]]
			};

			if (frm.doc.customer) {
				filters["customer"] = frm.doc.customer;
			}

			return {
				filters: filters
			}
		});

		if (frappe.model.can_read("Task")) {
			frm.add_custom_button(__("Gantt Chart"), function () {
				frappe.route_options = {
					"project": frm.doc.name
				};
				frappe.set_route("List", "Task", "Gantt");
			});

			frm.add_custom_button(__("Kanban Board"), () => {
				frappe.call('erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists', {
					project: frm.doc.project_name
				}).then(() => {
					frappe.set_route('List', 'Task', 'Kanban', frm.doc.project_name);
				});
			});
		}
	},

	refresh: function (frm) {
		if (frm.doc.__islocal) {
			frm.web_link && frm.web_link.remove();
		} else {
			frm.add_web_link("/projects?project=" + encodeURIComponent(frm.doc.name));

			frm.trigger('show_dashboard');
		}
	},
	tasks_refresh: function (frm) {
		var grid = frm.get_field('tasks').grid;
		grid.wrapper.find('select[data-fieldname="status"]').each(function () {
			if ($(this).val() === 'Open') {
				$(this).addClass('input-indicator-open');
			} else {
				$(this).removeClass('input-indicator-open');
			}
		});
	},
});

frappe.ui.form.on("Project Task", {
	edit_task: function(frm, doctype, name) {
		var doc = frappe.get_doc(doctype, name);
		if(doc.task_id) {
			frappe.set_route("Form", "Task", doc.task_id);
		} else {
			frappe.msgprint(__("Save the document first."));
		}
	},

	edit_timesheet: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.route_options = {"project": frm.doc.project_name, "task": child.task_id};
		frappe.set_route("List", "Timesheet");
	},

	make_timesheet: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.model.with_doctype('Timesheet', function() {
			var doc = frappe.model.get_new_doc('Timesheet');
			var row = frappe.model.add_child(doc, 'time_logs');
			row.project = frm.doc.project_name;
			row.task = child.task_id;
			frappe.set_route('Form', doc.doctype, doc.name);
		})
	},

	status: function(frm, doctype, name) {
		frm.trigger('tasks_refresh');
	},

	task_description:function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.task_description){
			erpnext.utils.get_description(child, "Task Description", child.task_description,"task_description", function(r){
				if(!r.exc){
					frappe.model.set_value(cdt,cdn,"description",r.message);
				}
			});
		}
	}
});

frappe.ui.form.on("Project", "validate", function (frm) {
	if (frm.doc.collect_progress == 1) {
		frappe.call({
			method: "erpnext.projects.doctype.project.project.times_check",
			args: {
				"from1": frm.doc.from,
				"to": frm.doc.to,
				"first_email": frm.doc.first_email,
				"second_email": frm.doc.second_email,
				"daily_time_to_send": frm.doc.daily_time_to_send,
				"weekly_time_to_send": frm.doc.weekly_time_to_send

			},
			callback: function (r) {
				frm.set_value("from", r.message.from1);
				frm.set_value("to", r.message.to);
				frm.set_value("first_email", r.message.first_email);
				frm.set_value("second_email", r.message.second_email);
				frm.set_value("daily_time_to_send", r.message.daily_time_to_send);
				frm.set_value("weekly_time_to_send", r.message.weekly_time_to_send);
			}
		});
	}
});