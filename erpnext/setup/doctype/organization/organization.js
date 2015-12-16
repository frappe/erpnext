// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.organization");

frappe.ui.form.on("Organization", {
	onload: function(frm) {
		erpnext.organization.setup_queries(frm);
	}, 
	
	onload_post_render: function(frm) {
		frm.get_field("delete_organization_transactions").$input.addClass("btn-danger");
	},
	country: function(frm) {
		erpnext.organization.set_chart_of_accounts_options(frm.doc);
	},
	delete_organization_transactions: function(frm) {
		frappe.verify_password(function() {
			var d = frappe.prompt({
				fieldtype:"Data",
				fieldname: "organization_name",
				label: __("Please re-type organization name to confirm"),
				reqd: 1,
				description: __("Please make sure you really want to delete all the transactions for this organization. Your master data will remain as it is. This action cannot be undone.")},
					function(data) {
						if(data.organization_name !== frm.doc.name) {
							frappe.msgprint("organization name not same");
							return;
						}
						frappe.call({
							method: "erpnext.setup.doctype.organization.delete_organization_transactions.delete_organization_transactions",
							args: {
								organization_name: data.organization_name
							},
							freeze: true,
							callback: function(r, rt) {
								if(!r.exc)
									frappe.msgprint(__("Successfully deleted all transactions related to this organization!"));
							},
							onerror: function() {
								frappe.msgprint(__("Wrong Password"));
							}
						});
					}, __("Delete all the Transactions for this organization"), __("Delete")
				);
				d.get_primary_btn().addClass("btn-danger");
			}
		);
	}
});


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.abbr && !doc.__islocal) {
		cur_frm.set_df_property("abbr", "read_only", 1);
	}

	if(!doc.__islocal) {
		cur_frm.toggle_enable("default_currency", (cur_frm.doc.__onload &&
			!cur_frm.doc.__onload.transactions_exist));
	}

	erpnext.organization.set_chart_of_accounts_options(doc);
}

erpnext.organization.set_chart_of_accounts_options = function(doc) {
	var selected_value = doc.chart_of_accounts;
	if(doc.country) {
		return frappe.call({
			method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
			args: {
				"country": doc.country,
			},
			callback: function(r) {
				if(!r.exc) {
					set_field_options("chart_of_accounts", [""].concat(r.message).join("\n"));
					if(in_list(r.message, selected_value))
						cur_frm.set_value("chart_of_accounts", selected_value);
				}
			}
		})
	}
}

cur_frm.cscript.change_abbr = function() {
	var dialog = new frappe.ui.Dialog({
		title: "Replace Abbr",
		fields: [
			{"fieldtype": "Data", "label": "New Abbreviation", "fieldname": "new_abbr",
				"reqd": 1 },
			{"fieldtype": "Button", "label": "Update", "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return frappe.call({
			method: "erpnext.setup.doctype.organization.organization.replace_abbr",
			args: {
				"organization": cur_frm.doc.name,
				"old": cur_frm.doc.abbr,
				"new": args.new_abbr
			},
			callback: function(r) {
				if(r.exc) {
					msgprint(__("There were errors."));
					return;
				} else {
					cur_frm.set_value("abbr", args.new_abbr);
				}
				dialog.hide();
				cur_frm.refresh();
			},
			btn: this
		})
	});
	dialog.show();
}

erpnext.organization.setup_queries = function(frm) {
	$.each([
		["default_bank_account", {"account_type": "Bank"}], 
		["default_cash_account", {"account_type": "Cash"}], 
		["default_receivable_account", {"account_type": "Receivable"}], 
		["default_payable_account", {"account_type": "Payable"}], 
		["default_expense_account", {"root_type": "Expense"}], 
		["default_income_account", {"root_type": "Income"}], 
		["round_off_account", {"root_type": "Expense"}],
		["cost_center", {}],
		["round_off_cost_center", {}]
	], function(i, v) {
		erpnext.organization.set_custom_query(frm, v);
	});
	
	if (sys_defaults.auto_accounting_for_stock) {
		$.each([
			["stock_adjustment_account", {"root_type": "Expense"}], 
			["expenses_included_in_valuation", {"root_type": "Expense"}],
			["stock_received_but_not_billed", {"report_type": "Balance Sheet"}]
		], function(i, v) {
			erpnext.organization.set_custom_query(frm, v);
		});
	}
}

erpnext.organization.set_custom_query = function(frm, v) {
	var filters = {
		"organization": frm.doc.name,
		"is_group": 0
	};
	for (var key in v[1]) 
		filters[key] = v[1][key];

	frm.set_query(v[0], function() {
		return {
			filters: filters
		};
	});
}