// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Structure Assignment', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query",
			}
		});
		frm.set_query("salary_structure", function() {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
					is_active: "Yes"
				}
			}
		});

		frm.set_query("income_tax_slab", function() {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
					disabled: 0,
					currency: frm.doc.currency
				}
			};
		});

		frm.set_query("payroll_payable_account", function() {
			var company_currency = erpnext.get_currency(frm.doc.company);
			return {
				filters: {
					"company": frm.doc.company,
					"root_type": "Liability",
					"is_group": 0,
					"account_currency": ["in", [frm.doc.currency, company_currency]],
				}
			}
		});
	},

	refresh: function(frm) {
		if(frm.doc.__onload){
			frm.unhide_earnings_and_taxation_section = frm.doc.__onload.earning_and_deduction_entries_does_not_exists;
			frm.trigger("set_earnings_and_taxation_section_visibility");
		}
	},

	employee: function(frm) {
		if(frm.doc.employee){
			frappe.call({
				method: "frappe.client.get_value",
				args:{
					doctype: "Employee",
					fieldname: "company",
					filters:{
						name: frm.doc.employee
					}
				},
				callback: function(data) {
					if(data.message){
						frm.set_value("company", data.message.company);
					}
				}
			});

			frm.trigger("valiadte_joining_date_and_salary_slips");
		}
		else{
			frm.set_value("company", null);
		}
	},

	company: function(frm) {
		if (frm.doc.company) {
			frappe.db.get_value("Company", frm.doc.company, "default_payroll_payable_account", (r) => {
				frm.set_value("payroll_payable_account", r.default_payroll_payable_account);
			});
		}
	},

	valiadte_joining_date_and_salary_slips: function(frm) {
		frappe.call({
			method: "earning_and_deduction_entries_does_not_exists",
			doc: frm.doc,
			callback: function(data) {
				let earning_and_deduction_entries_does_not_exists = data.message;
				frm.unhide_earnings_and_taxation_section = earning_and_deduction_entries_does_not_exists;
				frm.trigger("set_earnings_and_taxation_section_visibility");
			}
		});
	},

	set_earnings_and_taxation_section_visibility: function(frm) {
		if(frm.unhide_earnings_and_taxation_section){
			frm.set_df_property('earnings_and_taxation_section', 'hidden', 0);
		}
		else{
			frm.set_df_property('earnings_and_taxation_section', 'hidden', 1);
		}
	},

	from_date: function(frm) {
		if (frm.doc.from_date) {
			frm.trigger("valiadte_joining_date_and_salary_slips" );
		}
	},

});
