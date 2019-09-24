// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.ui.form.on("Project", {
	setup(frm) {
		frm.make_methods = {
			'Timesheet': () => {
				let doctype = 'Timesheet';
				frappe.model.with_doctype(doctype, () => {
					let new_doc = frappe.model.get_new_doc(doctype);

					// add a new row and set the project
					let time_log = frappe.model.get_new_doc('Timesheet Detail');
					time_log.project = frm.doc.name;
					new_doc.time_logs = [time_log];

					frappe.ui.form.make_quick_entry(doctype, null, null, new_doc);
				});
			},
		}
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
		frm.events.set_buttons(frm);
	},

	set_buttons: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Completed'), () => {
				frm.events.set_status(frm, 'Completed');
			}, __('Set Status'));

			frm.add_custom_button(__('Cancelled'), () => {
				frm.events.set_status(frm, 'Cancelled');
			}, __('Set Status'));
		}
	},

	set_status: function(frm, status) {
		frappe.confirm(__('Set Project and all Tasks to status {0}?', [status.bold()]), () => {
			frappe.xcall('erpnext.projects.doctype.project.project.set_project_status',
				{project: frm.doc.name, status: status}).then(() => { /* page will auto reload */ });
		});
	},

});
