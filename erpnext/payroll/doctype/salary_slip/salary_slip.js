// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('time_sheet', 'total_hours', 'working_hours');

frappe.ui.form.on("Salary Slip", {
	setup: function(frm) {
		$.each(["earnings", "deductions"], function(i, table_fieldname) {
			frm.get_field(table_fieldname).grid.editable_fields = [
				{fieldname: 'salary_component', columns: 6},
				{fieldname: 'amount', columns: 4}
			];
		});

		frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function() {
			return {
				filters: {
					employee: frm.doc.employee
				}
			};
		};

		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {
					type: "earning"
				}
			};
		});

		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {
					type: "deduction"
				}
			};
		});

		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		});
	},

	start_date: function(frm) {
		if (frm.doc.start_date) {
			frm.trigger("set_end_date");
		}
	},

	end_date: function(frm) {
		frm.events.get_emp_and_working_day_details(frm);
	},

	set_end_date: function(frm) {
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

	company: function(frm) {
		var company = locals[':Company'][frm.doc.company];
		if (!frm.doc.letter_head && company.default_letter_head) {
			frm.set_value('letter_head', company.default_letter_head);
		}
		frm.trigger("set_dynamic_labels");
	},

	set_dynamic_labels: function(frm) {
		var company_currency = frm.doc.company? erpnext.get_currency(frm.doc.company): frappe.defaults.get_default("currency");
		frappe.run_serially([
			() => 	frm.events.set_exchange_rate(frm, company_currency),
			() => 	frm.events.change_form_labels(frm, company_currency),
			() => 	frm.events.change_grid_labels(frm),
			() => 	frm.refresh_fields()
		]);
	},

	set_exchange_rate: function(frm, company_currency) {
		if (frm.doc.docstatus === 0) {
			if (frm.doc.currency) {
				var from_currency = frm.doc.currency;
				if (from_currency != company_currency) {
					frm.events.hide_loan_section(frm);
					frappe.call({
						method: "erpnext.setup.utils.get_exchange_rate",
						args: {
							from_currency: from_currency,
							to_currency: company_currency,
						},
						callback: function(r) {
							frm.set_value("exchange_rate", flt(r.message));
							frm.set_df_property('exchange_rate', 'hidden', 0);
							frm.set_df_property("exchange_rate", "description", "1 " + frm.doc.currency
								+ " = [?] " + company_currency);
						}
					});
				} else {
					frm.set_value("exchange_rate", 1.0);
					frm.set_df_property('exchange_rate', 'hidden', 1);
					frm.set_df_property("exchange_rate", "description", "" );
				}
			}
		}
	},

	exchange_rate: function(frm) {
		set_totals(frm);
	},

	hide_loan_section: function(frm) {
		frm.set_df_property('section_break_43', 'hidden', 1);
	},

	change_form_labels: function(frm, company_currency) {
		frm.set_currency_labels(["base_hour_rate", "base_gross_pay", "base_total_deduction",
			"base_net_pay", "base_rounded_total", "base_total_in_words", "base_year_to_date", "base_month_to_date"],
		company_currency);

		frm.set_currency_labels(["hour_rate", "gross_pay", "total_deduction", "net_pay", "rounded_total", "total_in_words", "year_to_date", "month_to_date"],
			frm.doc.currency);

		// toggle fields
		frm.toggle_display(["exchange_rate", "base_hour_rate", "base_gross_pay", "base_total_deduction",
			"base_net_pay", "base_rounded_total", "base_total_in_words", "base_year_to_date", "base_month_to_date"],
		frm.doc.currency != company_currency);
	},

	change_grid_labels: function(frm) {
		let fields = ["amount", "year_to_date", "default_amount", "additional_amount", "tax_on_flexible_benefit",
			"tax_on_additional_salary"];

		frm.set_currency_labels(fields, frm.doc.currency, "earnings");
		frm.set_currency_labels(fields, frm.doc.currency, "deductions");
	},

	refresh: function(frm) {
		frm.trigger("toggle_fields");

		var salary_detail_fields = ["formula", "abbr", "statistical_component", "variable_based_on_taxable_salary"];
		frm.fields_dict['earnings'].grid.set_column_disp(salary_detail_fields, false);
		frm.fields_dict['deductions'].grid.set_column_disp(salary_detail_fields, false);
		frm.trigger("set_dynamic_labels");
	},

	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields");
		frm.events.get_emp_and_working_day_details(frm);
	},

	payroll_frequency: function(frm) {
		frm.trigger("toggle_fields");
		frm.set_value('end_date', '');
	},

	employee: function(frm) {
		frm.events.get_emp_and_working_day_details(frm);
	},

	leave_without_pay: function(frm) {
		if (frm.doc.employee && frm.doc.start_date && frm.doc.end_date) {
			return frappe.call({
				method: 'process_salary_based_on_working_days',
				doc: frm.doc,
				callback: function() {
					frm.refresh();
				}
			});
		}
	},

	toggle_fields: function(frm) {
		frm.toggle_display(['hourly_wages', 'timesheets'], cint(frm.doc.salary_slip_based_on_timesheet)===1);

		frm.toggle_display(['payment_days', 'total_working_days', 'leave_without_pay'],
			frm.doc.payroll_frequency != "");
	},

	get_emp_and_working_day_details: function(frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: 'get_emp_and_working_day_details',
				doc: frm.doc,
				callback: function(r) {
					if (r.message[1] !== "Leave" && r.message[0]) {
						frm.fields_dict.absent_days.set_description(__("Unmarked Days is treated as {0}. You can can change this in {1}", [r.message, frappe.utils.get_form_link("Payroll Settings", "Payroll Settings", true)]));
					}
					frm.refresh();
				}
			});
		}
	}
});

frappe.ui.form.on('Salary Slip Timesheet', {
	time_sheet: function(frm) {
		set_totals(frm);
	},
	timesheets_remove: function(frm) {
		set_totals(frm);
	}
});

var set_totals = function(frm) {
	if (frm.doc.docstatus === 0) {
		if (frm.doc.earnings || frm.doc.deductions) {
			frappe.call({
				method: "set_totals",
				doc: frm.doc,
				callback: function() {
					frm.refresh_fields();
				}
			});
		}
	}
};

frappe.ui.form.on('Salary Detail', {
	amount: function(frm) {
		set_totals(frm);
	},

	earnings_remove: function(frm) {
		set_totals(frm);
	},

	deductions_remove: function(frm) {
		set_totals(frm);
	},

	salary_component: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.salary_component) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Salary Component",
					name: child.salary_component
				},
				callback: function(data) {
					if (data.message) {
						var result = data.message;
						frappe.model.set_value(cdt, cdn, 'condition', result.condition);
						frappe.model.set_value(cdt, cdn, 'amount_based_on_formula', result.amount_based_on_formula);
						if (result.amount_based_on_formula === 1) {
							frappe.model.set_value(cdt, cdn, 'formula', result.formula);
						} else {
							frappe.model.set_value(cdt, cdn, 'amount', result.amount);
						}
						frappe.model.set_value(cdt, cdn, 'statistical_component', result.statistical_component);
						frappe.model.set_value(cdt, cdn, 'depends_on_payment_days', result.depends_on_payment_days);
						frappe.model.set_value(cdt, cdn, 'do_not_include_in_total', result.do_not_include_in_total);
						frappe.model.set_value(cdt, cdn, 'variable_based_on_taxable_salary', result.variable_based_on_taxable_salary);
						frappe.model.set_value(cdt, cdn, 'is_tax_applicable', result.is_tax_applicable);
						frappe.model.set_value(cdt, cdn, 'is_flexible_benefit', result.is_flexible_benefit);
						refresh_field("earnings");
						refresh_field("deductions");
					}
				}
			});
		}
	},

	amount_based_on_formula: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.amount_based_on_formula === 1) {
			frappe.model.set_value(cdt, cdn, 'amount', null);
		} else {
			frappe.model.set_value(cdt, cdn, 'formula', null);
		}
	}
});
