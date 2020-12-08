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
	}
});
