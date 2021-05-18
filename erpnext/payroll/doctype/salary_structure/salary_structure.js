// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
{% include "erpnext/public/js/controllers/accounts.js" %}

cur_frm.add_fetch('company', 'default_letter_head', 'letter_head');


cur_frm.cscript.onload = function(doc, dt, dn){
	var e_tbl = doc.earnings || [];
	var d_tbl = doc.deductions || [];
	if (e_tbl.length == 0 && d_tbl.length == 0)
		return function(r, rt) { refresh_many(['earnings', 'deductions']);};
}

frappe.ui.form.on('Salary Structure', {
	onload: function(frm) {

		let help_button = $(`<a class = 'control-label'>
			${__("Condition and Formula Help")}
		</a>`).click(()=>{

			let d = new frappe.ui.Dialog({
				title: __('Condition and Formula Help'),
				fields: [
					{
						fieldname: 'msg_wrapper',
						fieldtype: 'HTML'
					}
				]
			});

			let message_html = frappe.render_template("condition_and_formula_help")

			d.fields_dict.msg_wrapper.$wrapper.append(message_html)

			d.show()
		});
		let help_button_wrapper = frm.get_field("conditions_and_formula_variable_and_example").$wrapper;
		help_button_wrapper.empty();
		help_button_wrapper.append(frm.doc.filters_html).append(help_button)

		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet)

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
		frm.trigger('set_earning_deduction_component');
	},

	set_earning_deduction_component: function(frm) {
		if(!frm.doc.company) return;
		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {type: "earning", company: frm.doc.company}
			};
		});
		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {type: "deduction", company: frm.doc.company}
			};
		});
	},

	company: function(frm) {
		frm.trigger('set_earning_deduction_component');
	},

	currency: function(frm) {
		calculate_totals(frm.doc);
		frm.trigger("set_dynamic_labels")
		frm.refresh()
	},

	set_dynamic_labels: function(frm) {
		frm.set_currency_labels(["net_pay","hour_rate", "leave_encashment_amount_per_day", "max_benefits", "total_earning",
			"total_deduction"], frm.doc.currency);

		frm.set_currency_labels(["amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
			frm.doc.currency, "earnings");

		frm.set_currency_labels(["amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
			frm.doc.currency, "deductions");

		frm.refresh_fields();
	},

	refresh: function(frm) {
		frm.trigger("set_dynamic_labels")
		frm.trigger("toggle_fields");
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);

		if(frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Preview Salary Slip"), function() {
				frm.trigger('preview_salary_slip');
			});
		}

		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__("Assign Salary Structure"), function() {
				var doc = frappe.model.get_new_doc('Salary Structure Assignment');
				doc.salary_structure = frm.doc.name;
				doc.company = frm.doc.company;
				frappe.set_route('Form', 'Salary Structure Assignment', doc.name);
			});
			frm.add_custom_button(__("Assign to Employees"),function () {
				frm.trigger('assign_to_employees')
			})
		}

		// set columns read-only
		let fields_read_only = ["is_tax_applicable", "is_flexible_benefit", "variable_based_on_taxable_salary"];
		fields_read_only.forEach(function(field) {
			frm.fields_dict.earnings.grid.update_docfield_property(
				field, 'read_only', 1
			);
			frm.fields_dict.deductions.grid.update_docfield_property(
				field, 'read_only', 1
			);
		});
		frm.trigger('set_earning_deduction_component');
	},

	assign_to_employees:function (frm) {
		var d = new frappe.ui.Dialog({
			title: __("Assign to Employees"),
			fields: [
				{fieldname: "sec_break", fieldtype: "Section Break", label: __("Filter Employees By (Optional)")},
				{fieldname: "grade", fieldtype: "Link", options: "Employee Grade", label: __("Employee Grade")},
				{fieldname:'department', fieldtype:'Link', options: 'Department', label: __('Department')},
				{fieldname:'designation', fieldtype:'Link', options: 'Designation', label: __('Designation')},
				{fieldname:"employee", fieldtype: "Link", options: "Employee", label: __("Employee")},
				{fieldname:"payroll_payable_account", fieldtype: "Link", options: "Account", filters: {"company": frm.doc.company, "root_type": "Liability", "is_group": 0, "account_currency": frm.doc.currency}, label: __("Payroll Payable Account")},
				{fieldname:'base_variable', fieldtype:'Section Break'},
				{fieldname:'from_date', fieldtype:'Date', label: __('From Date'), "reqd": 1},
				{fieldname:'income_tax_slab', fieldtype:'Link', label: __('Income Tax Slab'), options: 'Income Tax Slab'},
				{fieldname:'base_col_br', fieldtype:'Column Break'},
				{fieldname:'base', fieldtype:'Currency', label: __('Base')},
				{fieldname:'variable', fieldtype:'Currency', label: __('Variable')}
			],
			primary_action: function() {
				var data = d.get_values();
				delete data.company
				delete data.currency
				frappe.call({
					doc: frm.doc,
					method: "assign_salary_structure",
					args: data,
					callback: function(r) {
						if(!r.exc) {
							d.hide();
							frm.reload_doc();
						}
					}
				});
			},
			primary_action_label: __('Assign')
		});


		d.show();
	},

	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},

	preview_salary_slip: function(frm) {
		frappe.call({
			method: "erpnext.payroll.doctype.salary_structure.salary_structure.get_employees",
			args: {
				salary_structure: frm.doc.name
			},
			callback: function(r) {
				var employees = r.message;
				if(!employees) return;
				if (employees.length == 1){
					frm.events.open_salary_slip(frm, employees[0]);
				} else {
						var d = new frappe.ui.Dialog({
						title: __("Preview Salary Slip"),
						fields: [
							{
								"label":__("Employee"),
								"fieldname":"employee",
								"fieldtype":"Select",
								"reqd": true,
								options: employees
							}, {
								fieldname:"fetch",
								"label":__("Show Salary Slip"),
								"fieldtype":"Button"
							}
						]
					});
					d.get_input("fetch").on("click", function() {
						var values = d.get_values();
						if(!values) return;
							frm.events.open_salary_slip(frm, values.employee)

					});
					d.show();
				}
			}
		});
	},

	open_salary_slip: function(frm, employee){
		var print_format = frm.doc.salary_slip_based_on_timesheet ? "Salary Slip based on Timesheet" : "Salary Slip Standard";
		frappe.call({
			method: "erpnext.payroll.doctype.salary_structure.salary_structure.make_salary_slip",
			args: {
				source_name: frm.doc.name,
				employee: employee,
				as_print: 1,
				print_format: print_format,
				for_preview: 1
			},
			callback: function(r) {
				var new_window = window.open();
				new_window.document.write(r.message);
			}
		});
	},

	toggle_fields: function(frm) {
		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
	}
});

var validate_date = function(frm, cdt, cdn) {
	var doc = locals[cdt][cdn];
	if(doc.to_date && doc.from_date) {
		var from_date = frappe.datetime.str_to_obj(doc.from_date);
		var to_date = frappe.datetime.str_to_obj(doc.to_date);

		if(to_date < from_date) {
			frappe.model.set_value(cdt, cdn, "to_date", "");
			frappe.throw(__("From Date cannot be greater than To Date"));
		}
	}
}


cur_frm.cscript.amount = function(doc, cdt, cdn){
	calculate_totals(doc, cdt, cdn);
};

var calculate_totals = function(doc) {
	var tbl1 = doc.earnings || [];
	var tbl2 = doc.deductions || [];

	var total_earn = 0; var total_ded = 0;
	for(var i = 0; i < tbl1.length; i++){
		total_earn += flt(tbl1[i].amount);
	}
	for(var j = 0; j < tbl2.length; j++){
		total_ded += flt(tbl2[j].amount);
	}
	doc.total_earning = total_earn;
	doc.total_deduction = total_ded;
	doc.net_pay = 0.0
	if(doc.salary_slip_based_on_timesheet == 0){
		doc.net_pay = flt(total_earn) - flt(total_ded);
	}

	refresh_many(['total_earning', 'total_deduction', 'net_pay']);
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	calculate_totals(doc);
}


frappe.ui.form.on('Salary Detail', {
	amount: function(frm) {
		calculate_totals(frm.doc);
	},

	earnings_remove: function(frm) {
		calculate_totals(frm.doc);
	},

	deductions_remove: function(frm) {
		calculate_totals(frm.doc);
	},

	salary_component: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.salary_component){
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Salary Component",
					name: child.salary_component
				},
				callback: function(data) {
					if(data.message){
						var result = data.message;
						frappe.model.set_value(cdt, cdn, 'condition', result.condition);
						frappe.model.set_value(cdt, cdn, 'amount_based_on_formula', result.amount_based_on_formula);
						if(result.amount_based_on_formula == 1){
							frappe.model.set_value(cdt, cdn, 'formula', result.formula);
						}
						else{
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
		if(child.amount_based_on_formula == 1){
			frappe.model.set_value(cdt, cdn, 'amount', null);
		}
		else{
			frappe.model.set_value(cdt, cdn, 'formula', null);
		}
	}
})
