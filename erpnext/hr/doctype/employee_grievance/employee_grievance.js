// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Grievance', {
	setup: function(frm) {
		frm.set_query('grievance_against_party', function() {
			return {
				filters: {
					name: ['in', [
						'Company', 'Department', 'Employee Group', 'Employee Grade', 'Employee']
					]
				}
			};
		});
		frm.set_query('associated_document_type', function() {
			let ignore_modules = ["Setup", "Core", "Integrations", "Automation", "Website",
				"Utilities", "Event Streaming", "Social", "Chat", "Data Migration", "Printing", "Desk", "Custom"];
			return {
				filters: {
					istable: 0,
					issingle: 0,
					module: ["Not In", ignore_modules]
				}
			};
		});
	},

	refresh: function(frm) {
		if (!frm.doc.__islocal && frm.doc.status === "Resolved" && frm.doc.docstatus === 1) {
			if (frm.doc.employee_responsible) {
				if (frm.doc.is_applicable_for_suspension && (!(frm.doc.suspended_from && frm.doc.suspended_to) && !frm.doc.unsuspended_on)) {
					frm.add_custom_button(__("Suspend Employee"), function () {
						frm.events.suspend_or_unsuspend_employee(frm, 'suspend');
					});
				}

				if (frm.doc.is_applicable_for_pay_cut) {
					frm.add_custom_button(__("Apply Pay Cut"), function () {
						frm.events.create_additional_salary(frm);
					});
				}
			}

			if (frm.doc.suspended_from && frm.doc.suspended_to && !frm.doc.unsuspended_on) {
				let suspended_from = frappe.datetime.global_date_format(frm.doc.suspended_from);
				let suspended_to = frappe.datetime.global_date_format(frm.doc.suspended_to);

				let message =  __("Employee {0} is suspended from {1} to {2}. {0} will be unsuspended automatically on {2}.", [frm.doc.employee_responsible, suspended_from, suspended_to]);

				let html = '<span class="indicator whitespace-nowrap orange"><span>' + message;

				frm.dashboard.set_headline_alert(html);
				frm.dashboard.show();

				frm.add_custom_button(__("Unsuspend Employee"), function () {
					frm.events.suspend_or_unsuspend_employee(frm, "unsuspend");
					frm.refresh_fields();
				});
			}
		}
	},

	suspend_or_unsuspend_employee: function(frm, action) {
		let message = '';
		let method = '';
		if (action === 'suspend') {
			method = 'erpnext.hr.doctype.employee_grievance.employee_grievance.suspend_employee';
			message =  __('Are you sure you want to suspend the employee {0}', [frm.doc.employee_responsible]);
		} else if (action === 'unsuspend') {
			method = 'erpnext.hr.doctype.employee_grievance.employee_grievance.unsuspend_employee';
			message = __('Are you sure you want to unsuspend the employee {0}', [frm.doc.employee_responsible]);
		}
		if (frm.doc.employee_responsible) {
			frappe.confirm((message),
				function() {
					frappe.call({
						method: method,
						args: {
							doc: frm.doc
						},
						callback: function() {
							frm.refresh();
							cur_dialog.hide();
						}
					});
				},
				function() {
					cur_dialog.hide();
				}
			);
		}
	},

	create_additional_salary: function(frm) {
		frappe.call({
			method: "erpnext.hr.doctype.employee_grievance.employee_grievance.create_additional_salary",
			args: {
				doc: frm.doc
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

});
