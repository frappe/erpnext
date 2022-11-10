// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/vehicles/customer_vehicle_selector.js' %};

frappe.ui.form.on("Customer", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Lead': 'Lead',
		}

		frm.make_methods = {
			'Quotation': () => frappe.model.open_mapped_doc({
				method: 'erpnext.selling.doctype.customer.customer.make_quotation',
				frm: cur_frm
			}),
			'Opportunity': () => frappe.model.open_mapped_doc({
				method: 'erpnext.selling.doctype.customer.customer.make_opportunity',
				frm: cur_frm
			})
		}

		frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': 'Receivable',
				'company': d.company,
				"is_group": 0
			};

			if(doc.party_account_currency) {
				$.extend(filters, {"account_currency": doc.party_account_currency});
			}
			return {
				filters: filters
			}
		});
		frm.set_query('cost_center', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});

		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}

		frm.set_query('customer_primary_contact', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.name
				}
			}
		})
		frm.set_query('customer_primary_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.name
				}
			}
		})

		frm.set_query('default_bank_account', function() {
			return {
				filters: {
					'is_company_account': 1
				}
			}
		});
	},
	customer_primary_address: function(frm){
		if(frm.doc.customer_primary_address){
			frappe.call({
				method: 'erpnext.selling.doctype.customer.customer.get_primary_address_details',
				args: {
					"address_name": frm.doc.customer_primary_address
				},
				callback: function(r) {
					$.each(r.message || {}, (k, v) => {
						frm.set_value(k, v);
					})
				}
			});
		}
	},

	customer_primary_contact: function(frm){
		if(frm.doc.customer_primary_contact){
			frappe.call({
				method: 'erpnext.selling.doctype.customer.customer.get_primary_contact_details',
				args: {
					"contact_name": frm.doc.customer_primary_contact
				},
				callback: function(r) {
					$.each(r.message || {}, (k, v) => {
						frm.set_value(k, v);
					})
				}
			});
		}
	},

	is_internal_customer: function(frm) {
		if (frm.doc.is_internal_customer == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},

	loyalty_program: function(frm) {
		if(frm.doc.loyalty_program) {
			frm.set_value('loyalty_program_tier', null);
		}
	},

	refresh: function(frm) {
		if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Customer'}
		frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.set_route('query-report', 'General Ledger', {
					party_type: 'Customer',
					party: frm.doc.name,
					from_date: frappe.defaults.get_user_default("year_start_date"),
					to_date: frappe.defaults.get_user_default("year_end_date")
				});
			});

			frm.add_custom_button(__('Accounts Receivable'), function() {
				frappe.set_route('query-report', 'Accounts Receivable', {customer:frm.doc.name});
			});

			frm.add_custom_button(__('Ledger Summary'), function() {
				frappe.set_route('query-report', 'Customer Ledger Summary', {
					party: frm.doc.name,
					from_date: frappe.defaults.get_user_default("year_start_date"),
					to_date: frappe.defaults.get_user_default("year_end_date")
				});
			});

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			// indicator
			erpnext.utils.set_party_dashboard_indicators(frm);

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		var grid = cur_frm.get_field("sales_team").grid;
		grid.set_column_disp("allocated_amount", false);
		grid.set_column_disp("incentives", false);

		frm.events.make_customer_vehicle_selector(frm);
	},
	validate: function(frm) {
		if(frm.doc.lead_name) frappe.model.clear_doc("Lead", frm.doc.lead_name);

		erpnext.utils.format_ntn(frm, "tax_id");
		erpnext.utils.format_cnic(frm, "tax_cnic");
		erpnext.utils.format_strn(frm, "tax_strn");

		erpnext.utils.format_mobile_pakistan(frm, "mobile_no");
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no_2");
	},

	tax_id: function(frm) {
		erpnext.utils.format_ntn(frm, "tax_id");
		erpnext.utils.validate_duplicate_tax_id(frm.doc, "tax_id");
	},
	tax_cnic: function(frm) {
		erpnext.utils.format_cnic(frm, "tax_cnic");
		erpnext.utils.validate_duplicate_tax_id(frm.doc, "tax_cnic");
	},
	tax_strn: function(frm) {
		erpnext.utils.format_strn(frm, "tax_strn");
		erpnext.utils.validate_duplicate_tax_id(frm.doc, "tax_strn");
	},

	mobile_no: function (frm) {
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no");
	},
	mobile_no_2: function (frm) {
		erpnext.utils.format_mobile_pakistan(frm, "mobile_no_2");
	},

	make_customer_vehicle_selector: function (frm) {
		if (frm.fields_dict.customer_vehicle_selector_html && !frm.doc.__islocal) {
			frm.customer_vehicle_selector = erpnext.vehicles.make_customer_vehicle_selector(frm,
				frm.fields_dict.customer_vehicle_selector_html.wrapper,
				null,
				'name',
			);
		}
	},
});
