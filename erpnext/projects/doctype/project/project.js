// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Project", {
	onload: function(frm) {
		frm.hide_first = true;

		var so = frappe.meta.get_docfield("Project", "sales_order");
		so.get_route_options_for_new_doc = function(field) {
			if(frm.is_new()) return;
			return {
				"customer": frm.doc.customer,
				"project_name": frm.doc.name
			}
		}

		frm.set_query('customer', 'erpnext.controllers.queries.customer_query');

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
					frappe.route_options = {"project": frm.doc.name,
						"start": frm.doc.expected_start_date, "end": frm.doc.expected_end_date};
					frappe.set_route("Gantt", "Task");
				});
			}

			frm.dashboard.show_dashboard();
			frm.dashboard.add_section(frappe.render_template('project_dashboard', {project: frm.doc}));

			// var bars = [];
			// bars.push({
			// 	'title': __('Percent Complete'),
			// 	'width': (frm.doc.percent_complete || 1)  + '%',
			// 	'progress_class': 'progress-bar-success'
			// })
			//
			// var message = __("{0}% complete", [frm.doc.percent_complete]);
			//
			// frm.dashboard.add_progress(__('Status'), bars, message);

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

