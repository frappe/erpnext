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
			return {
				filters: {
					name: ['in', [
						"Salary Slip",
						"Payroll",
						"Employee Benefits",
						"Expense Claim",
						"Leave Encashment",
						"Employee Incentive"
					]]
				}
			};
		});
	},
	refresh: function(frm) {
		if (!frm.doc.__islocal && frm.doc.status === "Resolved" && frm.doc.docstatus === 1) {
			if (frm.doc.is_applicable_for_suspension && (!(frm.doc.suspended_from && frm.doc.suspended_to) && !frm.doc.unsuspended_on)) {
				frm.add_custom_button(__("Suspend Employee"), function () {
					frm.events.suspend_or_unsuspend_employee(frm, 'suspend');
				});
			}

			if (frm.doc.is_applicable_for_pay_cut) {
				frm.add_custom_button(__("Apply Pay-cut"), function () {
					frm.events.create_additional_salary(frm, );
				});
			}

			if (frm.doc.suspended_from && frm.doc.suspended_to) {
				let suspended_from = frappe.datetime.global_date_format(frm.doc.suspended_from);
				let suspended_to = frappe.datetime.global_date_format(frm.doc.suspended_to);

				let message_line1 = "Employee: <b>"+ frm.doc.employee_responsible +"</b> is suspended from <b>"+ suspended_from+"</b> to <b>" +suspended_to + "</b>.";
				let message_line2 = "Employee will be un-suspended automatically or you can do it manually by clicking on unsuspend Employee.";

				let html = '<span class="indicator whitespace-nowrap orange"><span>';
				html += message_line1;
				html += '</span></span><br><span>';
				html += message_line2+'</span>';

				frm.dashboard.set_headline_alert(html);
				frm.dashboard.show();

				frm.add_custom_button(__("Un-suspend Employee"), function () {
					frm.events.suspend_or_unsuspend_employee(frm, "unsuspend");
				});
			}
		}
	},
	suspend_or_unsuspend_employee: function(frm, action) {
		let message = '';
		let method = '';
		if (action === "suspend") {
			method = "erpnext.hr.doctype.employee_grievance.employee_grievance.suspend_employee";
			message =  __('Are you sure you want to Suspend');
			message += " "+frm.doc.employee_responsible+'?';
		} else if (action === "unsuspend") {
			method = "erpnext.hr.doctype.employee_grievance.employee_grievance.unsuspend_employee";
			message = __('Are you sure you want to Un-suspend');
			message += " "+frm.doc.employee_responsible+'?';
		}

		if (frm.doc.employee_responsible) {
			frappe.msgprint({
				title: __('Notification'),
				message: message,
				primary_action: {
					label: __('Yes'),
					action() {
						frappe.call({
							method: method,
							args: {
								name: frm.doc.name
							},
							callback: function () {
								frm.refresh();
								cur_dialog.hide();
							}
						});
					}
				}
			});
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
