// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var in_progress = false;

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on('Payroll Entry', {
	onload: function (frm) {
		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
		frm.events.department_filters(frm);
		frm.events.payroll_payable_account_filters(frm);
	},

	department_filters: function (frm) {
		frm.set_query("department", function () {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
	},

	payroll_payable_account_filters: function (frm) {
		frm.set_query("payroll_payable_account", function () {
			return {
				filters: {
					"company": frm.doc.company,
					"root_type": "Liability",
					"is_group": 0,
				}
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 0) {
			if (!frm.is_new()) {
				frm.page.clear_primary_action();
				frm.add_custom_button(__("Get Employees"),
					function () {
						frm.events.get_employee_details(frm);
					}
				).toggleClass('btn-primary', !(frm.doc.employees || []).length);
			}
			if ((frm.doc.employees || []).length && !frappe.model.has_workflow(frm.doctype)) {
				frm.page.clear_primary_action();
				frm.page.set_primary_action(__('Create Salary Slips'), () => {
					frm.save('Submit').then(() => {
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
		}).then(r => {
			if (r.docs && r.docs[0].employees) {
				frm.employees = r.docs[0].employees;
				frm.dirty();
				frm.save();
				frm.refresh();
				if (r.docs[0].validate_attendance) {
					render_employee_attendance(frm, r.message);
				}
			}
		});
	},

	create_salary_slips: function (frm) {
		frm.call({
			doc: frm.doc,
			method: "create_salary_slips",
			callback: function () {
				frm.refresh();
				frm.toolbar.refresh();
			}
		});
	},

	add_context_buttons: function (frm) {
		if (frm.doc.salary_slips_submitted || (frm.doc.__onload && frm.doc.__onload.submitted_ss)) {
			frm.events.add_bank_entry_button(frm);
		} else if (frm.doc.salary_slips_created) {
			frm.add_custom_button(__("Submit Salary Slip"), function () {
				submit_salary_slip(frm);
			}).addClass("btn-primary");
		}
	},

	add_bank_entry_button: function (frm) {
		frappe.call({
			method: 'erpnext.payroll.doctype.payroll_entry.payroll_entry.payroll_entry_has_bank_entries',
			args: {
				'name': frm.doc.name
			},
			callback: function (r) {
				if (r.message && !r.message.submitted) {
					frm.add_custom_button("Make Bank Entry", function () {
						make_bank_entry(frm);
					}).addClass("btn-primary");
				}
			}
		});
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
		});

		frm.set_query('employee', 'employees', () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Please set a Company"));
				return []
			}
			let filters = {};
			filters['company'] = frm.doc.company;
			filters['start_date'] = frm.doc.start_date;
			filters['end_date'] = frm.doc.end_date;

			if (frm.doc.department) {
				filters['department'] = frm.doc.department;
			}
			if (frm.doc.branch) {
				filters['branch'] = frm.doc.branch;
			}
			if (frm.doc.designation) {
				filters['designation'] = frm.doc.designation;
			}
			return {
				query: "erpnext.payroll.doctype.payroll_entry.payroll_entry.employee_query",
				filters: filters
			}
		});
	},

	payroll_frequency: function (frm) {
		frm.trigger("set_start_end_dates").then( ()=> {
			frm.events.clear_employee_table(frm);
		});
	},

	company: function (frm) {
		frm.events.clear_employee_table(frm);
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	currency: function (frm) {
		var company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}
		if (frm.doc.currency) {
			if (company_currency != frm.doc.currency) {
				frappe.call({
					method: "erpnext.setup.utils.get_exchange_rate",
					args: {
						from_currency: frm.doc.currency,
						to_currency: company_currency,
					},
					callback: function (r) {
						frm.set_value("exchange_rate", flt(r.message));
						frm.set_df_property('exchange_rate', 'hidden', 0);
						frm.set_df_property("exchange_rate", "description", "1 " + frm.doc.currency +
							" = [?] " + company_currency);
					}
				});
			} else {
				frm.set_value("exchange_rate", 1.0);
				frm.set_df_property('exchange_rate', 'hidden', 1);
				frm.set_df_property("exchange_rate", "description", "");
			}
		}
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
		if (!in_progress && frm.doc.start_date) {
			frm.trigger("set_end_date");
		} else {
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
				method: 'erpnext.payroll.doctype.payroll_entry.payroll_entry.get_start_end_dates',
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

	set_end_date: function (frm) {
		frappe.call({
			method: 'erpnext.payroll.doctype.payroll_entry.payroll_entry.get_end_date',
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

	validate_attendance: function (frm) {
		if (frm.doc.validate_attendance && frm.doc.employees) {
			frappe.call({
				method: 'validate_employee_attendance',
				args: {},
				callback: function (r) {
					render_employee_attendance(frm, r.message);
				},
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Validating Employee Attendance...')
			});
		} else {
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
		function () {
			frappe.call({
				method: 'submit_salary_slips',
				args: {},
				callback: function () {
					frm.events.refresh(frm);
				},
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Submitting Salary Slips and creating Journal Entry...')
			});
		},
		function () {
			if (frappe.dom.freeze_count) {
				frappe.dom.unfreeze();
				frm.events.refresh(frm);
			}
		}
	);
};

let make_bank_entry = function (frm) {
	var doc = frm.doc;
	if (doc.payment_account) {
		return frappe.call({
			doc: cur_frm.doc,
			method: "make_payment_entry",
			callback: function () {
				frappe.set_route(
					'List', 'Journal Entry', {
						"Journal Entry Account.reference_name": frm.doc.name
					}
				);
			},
			freeze: true,
			freeze_message: __("Creating Payment Entries......")
		});
	} else {
		frappe.msgprint(__("Payment Account is mandatory"));
		frm.scroll_to_field('payment_account');
	}
};

let render_employee_attendance = function (frm, data) {
	frm.fields_dict.attendance_detail_html.html(
		frappe.render_template('employees_to_mark_attendance', {
			data: data
		})
	);
};

frappe.ui.form.on('Payroll Employee Detail', {
	employee: function(frm) {
		if (!frm.doc.payroll_frequency) {
			frappe.throw(__("Please set a Payroll Frequency"));
		}
	}
});
