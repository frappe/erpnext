// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.company");

frappe.ui.form.on("Company", {
	setup: function(frm) {
		erpnext.company.setup_queries(frm);
		frm.set_query("hra_component", function(){
			return {
				filters: {"type": "Earning"}
			}
		});
		frm.set_query("arrear_component", function(){
			return {
				filters: {"is_additional_component": 1}
			}
		});
	},

	company_name: function(frm) {
		if(frm.doc.__islocal) {
			let parts = frm.doc.company_name.split();
			let abbr = $.map(parts, function (p) {
				return p? p.substr(0, 1) : null;
			}).join("");
			frm.set_value("abbr", abbr);
		}
	},

	date_of_commencement: function(frm) {
		if(frm.doc.date_of_commencement<frm.doc.date_of_incorporation)
		{
			frappe.throw(__("Date of Commencement should be greater than Date of Incorporation"));
		}
		if(!frm.doc.date_of_commencement){
			frm.doc.date_of_incorporation = ""
		}
	},

	refresh: function(frm) {
		if(frm.doc.abbr && !frm.doc.__islocal) {
			frm.set_df_property("abbr", "read_only", 1);
		}

		frm.toggle_display('address_html', !frm.doc.__islocal);
		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Company'}

			frm.toggle_enable("default_currency", (frm.doc.__onload &&
				!frm.doc.__onload.transactions_exist));

			frm.add_custom_button(__('Make Tax Template'), function() {
				frm.trigger("make_default_tax_template");
			});

			frm.add_custom_button(__('Cost Centers'), function() {
				frappe.set_route('Tree', 'Cost Center', {'company': frm.doc.name})
			}, __("View"));

			frm.add_custom_button(__('Chart of Accounts'), function() {
				frappe.set_route('Tree', 'Account', {'company': frm.doc.name})
			}, __("View"));

			frm.add_custom_button(__('Sales Tax Template'), function() {
				frappe.set_route('List', 'Sales Taxes and Charges Template', {'company': frm.doc.name});
			}, __("View"));

			frm.add_custom_button(__('Purchase Tax Template'), function() {
				frappe.set_route('List', 'Purchase Taxes and Charges Template', {'company': frm.doc.name});
			}, __("View"));

			frm.add_custom_button(__('Default Tax Template'), function() {
				frm.trigger("make_default_tax_template");
			}, __("Make"));
		}

		erpnext.company.set_chart_of_accounts_options(frm.doc);

	},

	make_default_tax_template: function(frm) {
		frm.call({
			method: "create_default_tax_template",
			doc: frm.doc,
			freeze: true,
			callback: function() {
				frappe.msgprint(__("Default tax templates for sales and purchase are created."));
			}
		})
	},

	onload_post_render: function(frm) {
		if(frm.get_field("delete_company_transactions").$input)
			frm.get_field("delete_company_transactions").$input.addClass("btn-danger");
	},

	country: function(frm) {
		erpnext.company.set_chart_of_accounts_options(frm.doc);
	},

	delete_company_transactions: function(frm) {
		frappe.verify_password(function() {
			var d = frappe.prompt({
				fieldtype:"Data",
				fieldname: "company_name",
				label: __("Please re-type company name to confirm"),
				reqd: 1,
				description: __("Please make sure you really want to delete all the transactions for this company. Your master data will remain as it is. This action cannot be undone.")
			},
			function(data) {
				if(data.company_name !== frm.doc.name) {
					frappe.msgprint(__("Company name not same"));
					return;
				}
				frappe.call({
					method: "erpnext.setup.doctype.company.delete_company_transactions.delete_company_transactions",
					args: {
						company_name: data.company_name
					},
					freeze: true,
					callback: function(r, rt) {
						if(!r.exc)
							frappe.msgprint(__("Successfully deleted all transactions related to this company!"));
					},
					onerror: function() {
						frappe.msgprint(__("Wrong Password"));
					}
				});
			},
			__("Delete all the Transactions for this Company"), __("Delete")
			);
			d.get_primary_btn().addClass("btn-danger");
		});
	}
});


erpnext.company.set_chart_of_accounts_options = function(doc) {
	var selected_value = doc.chart_of_accounts;
	if(doc.country) {
		return frappe.call({
			method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
			args: {
				"country": doc.country,
				"with_standard": true
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
		var args = dialog.get_values();
		if(!args) return;
		frappe.show_alert(__("Update in progress. It might take a while."));
		return frappe.call({
			method: "erpnext.setup.doctype.company.company.enqueue_replace_abbr",
			args: {
				"company": cur_frm.doc.name,
				"old": cur_frm.doc.abbr,
				"new": args.new_abbr
			},
			callback: function(r) {
				if(r.exc) {
					frappe.msgprint(__("There were errors."));
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

erpnext.company.setup_queries = function(frm) {
	$.each([
		["default_bank_account", {"account_type": "Bank"}],
		["default_cash_account", {"account_type": "Cash"}],
		["default_receivable_account", {"account_type": "Receivable"}],
		["default_payable_account", {"account_type": "Payable"}],
		["default_expense_account", {"root_type": "Expense"}],
		["default_income_account", {"root_type": "Income"}],
		["default_payroll_payable_account", {"root_type": "Liability"}],
		["round_off_account", {"root_type": "Expense"}],
		["write_off_account", {"root_type": "Expense"}],
		["discount_allowed_account", {"root_type": "Expense"}],
		["discount_received_account", {"root_type": "Income"}],
		["exchange_gain_loss_account", {"root_type": "Expense"}],
		["unrealized_exchange_gain_loss_account", {"root_type": "Expense"}],
		["accumulated_depreciation_account",
			{"root_type": "Asset", "account_type": "Accumulated Depreciation"}],
		["depreciation_expense_account", {"root_type": "Expense", "account_type": "Depreciation"}],
		["disposal_account", {"report_type": "Profit and Loss"}],
		["default_inventory_account", {"account_type": "Stock"}],
		["cost_center", {}],
		["round_off_cost_center", {}],
		["depreciation_cost_center", {}],
		["default_employee_advance_account", {"root_type": "Asset"}],
		["expenses_included_in_asset_valuation", {"account_type": "Expenses Included In Asset Valuation"}],
		["capital_work_in_progress_account", {"account_type": "Capital Work in Progress"}],
		["asset_received_but_not_billed", {"account_type": "Asset Received But Not Billed"}]
	], function(i, v) {
		erpnext.company.set_custom_query(frm, v);
	});

	if (frm.doc.enable_perpetual_inventory) {
		$.each([
			["stock_adjustment_account",
				{"root_type": "Expense", "account_type": "Stock Adjustment"}],
			["expenses_included_in_valuation",
				{"root_type": "Expense", "account_type": "Expenses Included in Valuation"}],
			["stock_received_but_not_billed",
				{"root_type": "Liability", "account_type": "Stock Received But Not Billed"}]
		], function(i, v) {
			erpnext.company.set_custom_query(frm, v);
		});
	}
}

erpnext.company.set_custom_query = function(frm, v) {
	var filters = {
		"company": frm.doc.name,
		"is_group": 0
	};

	for (var key in v[1]) {
		filters[key] = v[1][key];
	}

	frm.set_query(v[0], function() {
		return {
			filters: filters
		}
	});
}
