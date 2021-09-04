// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var in_progress = false;

frappe.ui.form.on('Payroll Entry', {
	onload: function (frm) {
		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);

		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
	},

	refresh: function(frm) {
		erpnext.hide_company();
		if (frm.doc.docstatus == 0) {
			if(!frm.is_new()) {
				frm.page.clear_primary_action();
				frm.add_custom_button(__("Get Employees"),
					function() {
						frm.events.get_employee_details(frm);
					}
				).toggleClass('btn-primary', !(frm.doc.employees || []).length);
			}
			if ((frm.doc.employees || []).length) {
				frm.page.set_primary_action(__('Create Salary Slips'), () => {
					frm.save('Submit').then(()=>{
						frm.page.clear_primary_action();
						frm.refresh();
						frm.events.refresh(frm);
					});
				});
			}
		}
		if (frm.doc.docstatus == 1) {
			if (frm.custom_buttons) frm.clear_custom_buttons();
			frm.events.add_context_buttons(frm);
		}
	},

	get_employee_details: function (frm) {
		return frappe.call({
			doc: frm.doc,
			method: 'fill_employee_details',
			callback: function(r) {
				if (r.docs[0].employees){
					frm.save();
					frm.refresh();
					if(r.docs[0].validate_attendance){
						render_employee_attendance(frm, r.message);
					}
				}
			}
		})
	},

	create_salary_slips: function(frm) {
		frm.call({
			doc: frm.doc,
			method: "create_salary_slips",
			callback: function(r) {
				frm.refresh();
				frm.toolbar.refresh();
			}
		})
	},

	update_salary_slips: function(frm) {
		frm.call({
			doc: frm.doc,
			method: "update_salary_slips",
		})
	},

	add_context_buttons: function(frm) {
		if(frm.doc.salary_slips_submitted || (frm.doc.__onload && frm.doc.__onload.submitted_ss)) {
			frm.events.add_bank_entry_button(frm);
		} else if(frm.doc.salary_slips_created) {
			frm.add_custom_button(__("Update Salary Slips"), function () {
				frm.trigger("update_salary_slips");
			});

			frm.add_custom_button(__("Submit Salary Slip"), function() {
				submit_salary_slip(frm);
			}).addClass("btn-primary");
		}
	},

	make_disbursement_entry: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_disbursement_mode_details",
			callback: function(r) {
				if (r && r.message) {
					let salary_modes = r.message[0]
					let banks = r.message[1]
					let d = new frappe.ui.Dialog({
						title: 'Select Salary Mode',
						fields: [
							{
								label: 'Payment Account',
								fieldname: 'payment_account',
								fieldtype: 'Link',
								options: "Account",
								reqd: 1,
								get_query: function () {
									return {
										filters: {
											company: frm.doc.company,
											is_group: 0,
											account_type: ['in', ['Cash', 'Bank']]
										}
									}
								}
							},
							{
								label: 'Salary Mode',
								fieldname: 'salary_mode',
								fieldtype: 'Select',
								options: salary_modes
							},
							{
								label: 'Bank',
								fieldname: 'bank_name',
								fieldtype: 'Select',
								options: banks,
								depends_on: "eval:doc.salary_mode == 'Bank'"
							},
							{
								label: 'Employee',
								fieldname: 'employee',
								fieldtype: 'Link',
								options: 'Employee',
								onchange: function () {
									var employee = d.get_value('employee');
									if (employee) {
										frappe.db.get_value("Employee", employee, "employee_name", (r) => {
											if (r) {
												d.set_value('employee_name', r.employee_name);
											}
										});
									} else {
										d.set_value('employee_name', '');
									}
								}
							},
							{
								label: 'Employee Name',
								fieldname: 'employee_name',
								fieldtype: 'Data',
								read_only: 1,
							},
						],
						primary_action_label: 'Submit',
						primary_action: function(r) {
							return frappe.call({
								doc: cur_frm.doc,
								method: "make_payment_entry",
								args: {
									payment_account: r.payment_account,
									salary_mode: r.salary_mode,
									bank_name: r.bank_name,
									employee: r.employee,
								},
								freeze: true,
								freeze_message: __("Creating Payment Entry......"),
								callback: function(r) {
									if (r.message && r.message.length) {
										if (r.message.length === 1) {
											frappe.set_route('Form', 'Journal Entry', r.message[0]);
										} else {
											frappe.set_route('List', 'Journal Entry',
												{"Journal Entry Account.reference_name": frm.doc.name});
										}
									}
								}
							});
						}
					});
					d.show();
				}
			}
		});
	},

	add_bank_entry_button: function(frm) {
		if (!frm.doc.__onload || !frm.doc.__onload.has_bank_entries) {
			frm.add_custom_button("Make Payment Voucher", function() {
				frm.trigger("make_disbursement_entry");
			}).addClass("btn-primary");
		}
	},

	setup: function (frm) {
		frm.add_fetch('company', 'cost_center', 'cost_center');

		frm.set_query("payment_account", function () {
			var account_types = ["Bank", "Cash"];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		}),
		frm.set_query("cost_center", function () {
			return {
				filters: {
					"is_group": 0,
					company: frm.doc.company
				}
			};
		}),
		frm.set_query("project", function () {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	},

	payroll_frequency: function (frm) {
		frm.trigger("set_start_end_dates");
		frm.events.clear_employee_table(frm);
	},

	company: function (frm) {
		frm.events.clear_employee_table(frm);
	},

	department: function (frm) {
		frm.events.clear_employee_table(frm);
	},

	designation: function (frm) {
		frm.events.clear_employee_table(frm);
	},

	branch: function (frm) {
		frm.events.clear_employee_table(frm);
	},

	start_date: function (frm) {
		if(!in_progress && frm.doc.start_date){
			frm.trigger("set_end_date");
		}else{
			// reset flag
			in_progress = false;
		}
		frm.events.clear_employee_table(frm);
	},

	project: function (frm) {
		frm.events.clear_employee_table(frm);
	},

	salary_slip_based_on_timesheet: function (frm) {
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
	},

	set_start_end_dates: function (frm) {
		if (!frm.doc.salary_slip_based_on_timesheet) {
			frappe.call({
				method: 'erpnext.hr.doctype.payroll_entry.payroll_entry.get_start_end_dates',
				args: {
					payroll_frequency: frm.doc.payroll_frequency,
					start_date: frm.doc.posting_date
				},
				callback: function (r) {
					if (r.message) {
						in_progress = true;
						frm.set_value('start_date', r.message.start_date);
						frm.set_value('end_date', r.message.end_date);
					}
				}
			});
		}
	},

	set_end_date: function(frm){
		frappe.call({
			method: 'erpnext.hr.doctype.payroll_entry.payroll_entry.get_end_date',
			args: {
				frequency: frm.doc.payroll_frequency,
				start_date: frm.doc.start_date
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value('end_date', r.message.end_date);
				}
			}
		});
	},

	validate_attendance: function(frm){
		if(frm.doc.validate_attendance && frm.doc.employees){
			frappe.call({
				method: 'validate_employee_attendance',
				args: {},
				callback: function(r) {
					render_employee_attendance(frm, r.message);
				},
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Validating Employee Attendance...')
			});
		}else{
			frm.fields_dict.attendance_detail_html.html("");
		}
	},

	clear_employee_table: function (frm) {
		frm.clear_table('employees');
		frm.refresh();
	},
});

// Submit salary slips

const submit_salary_slip = function (frm) {
	frappe.confirm(__('This will submit Salary Slips and create accrual Journal Entry. Do you want to proceed?'),
		function() {
			frappe.call({
				method: 'submit_salary_slips',
				args: {},
				callback: function() {frm.events.refresh(frm);},
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Submitting Salary Slips and creating Journal Entry...')
			});
		},
		function() {
			if(frappe.dom.freeze_count) {
				frappe.dom.unfreeze();
				frm.events.refresh(frm);
			}
		}
	);
};

let render_employee_attendance = function(frm, data) {
	frm.fields_dict.attendance_detail_html.html(
		frappe.render_template('employees_to_mark_attendance', {
			data: data
		})
	);
}
