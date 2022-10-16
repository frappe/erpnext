// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
//frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on('Budget', {
	onload: function(frm) {
		frm.set_query("account", "accounts", function() {
			return {
				filters: {
					company: frm.doc.company,
					report_type: "Profit and Loss",
					is_group: 0
				}
			};
		});

		frm.set_query("monthly_distribution", function() {
			return {
				filters: {
					fiscal_year: frm.doc.fiscal_year
				}
			};
		});
		//erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function(frm) {
		frm.trigger("toggle_reqd_fields")
		frm.get_field("accounts").grid.grid_pagination.page_length = 150
	},

	budget_against: function(frm) {
		frm.trigger("set_null_value")
		frm.trigger("toggle_reqd_fields")
	},

	set_null_value: function(frm) {
		if(frm.doc.budget_against == 'Cost Center') {
			frm.set_value('project', null)
		} else {
			frm.set_value('cost_center', null)
		}
	},
	get_accounts: function(frm) {
		if(frm.doc.cost_center || frm.doc.project){
			return frappe.call({
				method: "get_accounts",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("accounts");
					frm.refresh_fields();
				},
				freeze: true,
				freeze_message: "Loading Expense Accounts..... Please Wait"
			});
		}else{
			frappe.throw("Either Cost Center or Project is missing. ")
		}
	},
	toggle_reqd_fields: function(frm) {
		frm.toggle_reqd("cost_center", frm.doc.budget_against=="Cost Center");
		frm.toggle_reqd("project", frm.doc.budget_against=="Project");
	}
});

frappe.ui.form.on("Budget Account", {
	initial_budget: function (frm, doctype, name) {
		var d = locals[doctype][name];
		if(d.initial_budget >0){
			frappe.model.set_value(doctype, name, "budget_amount", d.initial_budget);
		}
	},
});
