// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.company");

frappe.ui.form.on("Company", {
	onload: function(frm) {
		if (frm.doc.__islocal && frm.doc.parent_company) {
			frappe.db.get_value('Company', frm.doc.parent_company, 'is_group', (r) => {
				if (!r.is_group) {
					frm.set_value('parent_company', '');
				}
			});
		}

		frm.call('check_if_transactions_exist').then(r => {
			frm.toggle_enable("default_currency", (!r.message));
		});
	},
	setup: function(frm) {
		frm.__rename_queue = "long";
		erpnext.company.setup_queries(frm);

		frm.set_query("parent_company", function() {
			return {
				filters: {"is_group": 1}
			}
		});

		frm.set_query("default_selling_terms", function() {
			return { filters: { selling: 1 } };
		});

		frm.set_query("default_buying_terms", function() {
			return { filters: { buying: 1 } };
		});

		frm.set_query("default_in_transit_warehouse", function() {
			return {
				filters:{
					'warehouse_type' : 'Transit',
					'is_group': 0,
					'company': frm.doc.company_name
				}
			};
		});
	},

	company_name: function(frm) {
		if(frm.doc.__islocal) {
			// add missing " " arg in split method
			let parts = frm.doc.company_name.split(" ");
			let abbr = $.map(parts, function (p) {
				return p? p.substr(0, 1) : null;
			}).join("");
			frm.set_value("abbr", abbr);
		}
	},

	parent_company: function(frm) {
		var bool = frm.doc.parent_company ? true : false;
		frm.set_value('create_chart_of_accounts_based_on', bool ? "Existing Company" : "");
		frm.set_value('existing_company', bool ? frm.doc.parent_company : "");
		disbale_coa_fields(frm, bool);
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
		frm.toggle_display('address_html', !frm.is_new());

		if (!frm.is_new()) {
			frm.doc.abbr && frm.set_df_property("abbr", "read_only", 1);
			disbale_coa_fields(frm);
			frappe.contacts.render_address_and_contact(frm);

			frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Company'}

			if (frappe.perm.has_perm("Cost Center", 0, 'read')) {
				frm.add_custom_button(__('Cost Centers'), function() {
					frappe.set_route('Tree', 'Cost Center', {'company': frm.doc.name});
				}, __("View"));
			}

			if (frappe.perm.has_perm("Account", 0, 'read')) {
				frm.add_custom_button(__('Chart of Accounts'), function() {
					frappe.set_route('Tree', 'Account', {'company': frm.doc.name});
				}, __("View"));
			}

			if (frappe.perm.has_perm("Sales Taxes and Charges Template", 0, 'read')) {
				frm.add_custom_button(__('Sales Tax Template'), function() {
					frappe.set_route('List', 'Sales Taxes and Charges Template', {'company': frm.doc.name});
				}, __("View"));
			}

			if (frappe.perm.has_perm("Purchase Taxes and Charges Template", 0, 'read')) {
				frm.add_custom_button(__('Purchase Tax Template'), function() {
					frappe.set_route('List', 'Purchase Taxes and Charges Template', {'company': frm.doc.name});
				}, __("View"));
			}

			if (frm.has_perm('write')) {
				frm.add_custom_button(__('Create Tax Template'), function() {
					frm.trigger("make_default_tax_template");
				}, __('Manage'));
			}

			if (frappe.user.has_role('System Manager')) {
				if (frm.has_perm('write')) {
					frm.add_custom_button(__('Delete Transactions'), function() {
						frm.trigger("delete_company_transactions");
					}, __('Manage'));
				}
			}
		}

		erpnext.company.set_chart_of_accounts_options(frm.doc);
	},

	make_default_tax_template: function(frm) {
		frm.call({
			method: "create_default_tax_template",
			doc: frm.doc,
			freeze: true,
			callback: function() {
				frappe.msgprint(__("Default tax templates for sales, purchase and items are created."));
			}
		})
	},

	country: function(frm) {
		erpnext.company.set_chart_of_accounts_options(frm.doc);
	},

	delete_company_transactions: function(frm) {
		frappe.verify_password(function() {
			var d = frappe.prompt({
				fieldtype:"Data",
				fieldname: "company_name",
				label: __("Please enter the company name to confirm"),
				reqd: 1,
				description: __("Please make sure you really want to delete all the transactions for this company. Your master data will remain as it is. This action cannot be undone.")
			},
			function(data) {
				if(data.company_name !== frm.doc.name) {
					frappe.msgprint(__("Company name not same"));
					return;
				}
				frappe.call({
					method: "erpnext.setup.doctype.company.company.create_transaction_deletion_request",
					args: {
						company: data.company_name
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

erpnext.company.setup_queries = function(frm) {
	$.each([
		["default_bank_account", {"account_type": "Bank"}],
		["default_cash_account", {"account_type": "Cash"}],
		["default_receivable_account", {"account_type": "Receivable"}],
		["default_payable_account", {"account_type": "Payable"}],
		["default_expense_account", {"root_type": "Expense"}],
		["default_income_account", {"root_type": "Income"}],
		["round_off_account", {"root_type": "Expense"}],
		["write_off_account", {"root_type": "Expense"}],
		["default_deferred_expense_account", {}],
		["default_deferred_revenue_account", {}],
		["default_discount_account", {}],
		["discount_allowed_account", {"root_type": "Expense"}],
		["discount_received_account", {"root_type": "Income"}],
		["exchange_gain_loss_account", {"root_type": ["in", ["Expense", "Income"]]}],
		["unrealized_exchange_gain_loss_account", {"root_type": ["in", ["Expense", "Income"]]}],
		["accumulated_depreciation_account",
			{"root_type": "Asset", "account_type": "Accumulated Depreciation"}],
		["depreciation_expense_account", {"root_type": "Expense", "account_type": "Depreciation"}],
		["disposal_account", {"report_type": "Profit and Loss"}],
		["default_inventory_account", {"account_type": "Stock"}],
		["cost_center", {}],
		["round_off_cost_center", {}],
		["depreciation_cost_center", {}],
		["capital_work_in_progress_account", {"account_type": "Capital Work in Progress"}],
		["asset_received_but_not_billed", {"account_type": "Asset Received But Not Billed"}],
		["unrealized_profit_loss_account", {"root_type": ["in", ["Liability", "Asset"]]}],
		["default_provisional_account", {"root_type": ["in", ["Liability", "Asset"]]}]
	], function(i, v) {
		erpnext.company.set_custom_query(frm, v);
	});

	if (frm.doc.enable_perpetual_inventory) {
		$.each([
			["stock_adjustment_account",
				{"root_type": "Expense", "account_type": "Stock Adjustment"}],
			["stock_received_but_not_billed",
				{"root_type": "Liability", "account_type": "Stock Received But Not Billed"}],
			["service_received_but_not_billed",
				{"root_type": "Liability", "account_type": "Service Received But Not Billed"}],

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

var disbale_coa_fields = function(frm, bool=true) {
	frm.set_df_property("create_chart_of_accounts_based_on", "read_only", bool);
	frm.set_df_property("chart_of_accounts", "read_only", bool);
	frm.set_df_property("existing_company", "read_only", bool);
}
