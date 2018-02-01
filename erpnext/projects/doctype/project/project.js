// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Project", {
	setup: function(frm) {
		frm.set_indicator_formatter('title',
			function(doc) {
				let indicator = 'orange';
				if (doc.status == 'Overdue') {
					indicator = 'red';
				}
				else if (doc.status == 'Cancelled') {
					indicator = 'dark grey';
				}
				else if (doc.status == 'Closed') {
					indicator = 'green';
				}
				return indicator;
			}
		);
	},

	onload: function(frm) {
		var so = frappe.meta.get_docfield("Project", "sales_order");
		so.get_route_options_for_new_doc = function(field) {
			if(frm.is_new()) return;
			return {
				"customer": frm.doc.customer,
				"project_name": frm.doc.name
			}
		}

		frm.set_query('customer', 'erpnext.controllers.queries.customer_query');

		frm.set_query("user", "users", function() {
			return {
				query:"erpnext.projects.doctype.project.project.get_users_for_project"
			}
		});

		// sales order
		frm.set_query('sales_order', function() {
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
	},

	refresh: function(frm) {
		if(frm.doc.__islocal) {
			frm.web_link && frm.web_link.remove();
		} else {
			frm.add_web_link("/projects?project=" + encodeURIComponent(frm.doc.name));

			if(frappe.model.can_read("Task")) {
				frm.add_custom_button(__("Gantt Chart"), function() {
					frappe.route_options = {"project": frm.doc.name};
					frappe.set_route("List", "Task", "Gantt");
				});
			}

			frm.trigger('show_dashboard');
		}
	},
	tasks_refresh: function(frm) {
		var grid = frm.get_field('tasks').grid;
		grid.wrapper.find('select[data-fieldname="status"]').each(function() {
			if($(this).val()==='Open') {
				$(this).addClass('input-indicator-open');
			} else {
				$(this).removeClass('input-indicator-open');
			}
		});
	},
	show_dashboard: function(frm) {
		if(frm.doc.__onload.activity_summary.length) {
			var hours = $.map(frm.doc.__onload.activity_summary, function(d) { return d.total_hours });
			var max_count = Math.max.apply(null, hours);
			var sum = hours.reduce(function(a, b) { return a + b; }, 0);
			var section = frm.dashboard.add_section(
				frappe.render_template('project_dashboard',
					{
						data: frm.doc.__onload.activity_summary,
						max_count: max_count,
						sum: sum
					}));

			section.on('click', '.time-sheet-link', function() {
				var activity_type = $(this).attr('data-activity_type');
				frappe.set_route('List', 'Timesheet',
					{'activity_type': activity_type, 'project': frm.doc.name, 'status': ["!=", "Cancelled"]});
			});
		}
	}
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
});
