// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.item");

frappe.ui.form.on("Item", {
	onload: function(frm) {
		var df = frappe.meta.get_docfield("Item Variant", "item_attribute_value");
		df.on_make = function(field) {
			field.$input.autocomplete({
				minLength: 0,
				minChars: 0,
				source: function(request, response) {
					frappe.call({
						method:"frappe.client.get_list",
						args:{
							doctype:"Item Attribute Value",
							filters: [
								["parent","=", field.doc.item_attribute],
								["attribute_value", "like", request.term + "%"]
							],
							fields: ["attribute_value"]
						},
						callback: function(r) {
							response($.map(r.message, function(d) { return d.attribute_value; }));
						}
					});
				},
				select: function(event, ui) {
					field.$input.val(ui.item.value);
					field.$input.trigger("change");
				},
				focus: function( event, ui ) {
					if(ui.item.action) {
						return false;
					}
				},
			});
		}

		erpnext.item.setup_queries(frm);
	},

	refresh: function(frm) {
		if(frm.doc.is_stock_item) {
			frm.add_custom_button(__("Show Balance"), function() {
				frappe.route_options = {
					"item_code": frm.doc.name
				}
				frappe.set_route("query-report", "Stock Balance");
			});
		}

		// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
		// read only if any stock ledger entry exists
		erpnext.item.make_dashboard(frm);

		if (frm.doc.has_variants) {
			frm.set_intro(__("This Item is a Template and cannot be used in transactions. Item attributes will be copied over into the variants unless 'No Copy' is set"), true);
			frm.add_custom_button(__("Show Variants"), function() {
				frappe.set_route("List", "Item", {"variant_of": frm.doc.name});
			}, "icon-list", "btn-default");
		}
		if (frm.doc.variant_of) {
			frm.set_intro(__("This Item is a Variant of {0} (Template). Attributes will be copied over from the template unless 'No Copy' is set", [frm.doc.variant_of]), true);
		}

		if (frappe.defaults.get_default("item_naming_by")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		erpnext.item.edit_prices_button(frm);

		if (!frm.doc.__islocal && frm.doc.is_stock_item == 'Yes') {
			frm.toggle_enable(['has_serial_no', 'is_stock_item', 'valuation_method', 'has_batch_no'],
				(frm.doc.__onload && frm.doc.__onload.sle_exists=="exists") ? false : true);
		}

		erpnext.item.toggle_reqd(frm);
	},

	validate: function(frm){
		erpnext.item.weight_to_validate(frm);
	},

	image: function(frm) {
		refresh_field("image_view");
	},

	page_name: frappe.utils.warn_page_name_change,

	item_code: function(frm) {
		if(!frm.doc.item_name)
			frm.set_value("item_name", frm.doc.item_code);
		if(!frm.doc.description)
			frm.set_value("description", frm.doc.item_code);
	},

	tax_type: function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		return get_server_fields('get_tax_rate', d.tax_type, 'taxes', doc, cdt, cdn, 1);
	},

	copy_from_item_group: function(frm) {
		return frm.call({
			doc: frm.doc,
			method: "copy_specification_from_item_group"
		});
	},
	is_stock_item: function(frm) {
		erpnext.item.toggle_reqd(frm);
	}
});

$.extend(erpnext.item, {
	setup_queries: function(frm) {
		// Expense Account
		// ---------------------------------
		frm.fields_dict['expense_account'].get_query = function(doc) {
			return {
				filters: {
					"report_type": "Profit and Loss",
					"group_or_ledger": "Ledger"
				}
			}
		}

		// Income Account
		// --------------------------------
		frm.fields_dict['income_account'].get_query = function(doc) {
			return {
				filters: {
					"report_type": "Profit and Loss",
					'group_or_ledger': "Ledger",
					'account_type': "Income Account"
				}
			}
		}


		// Purchase Cost Center
		// -----------------------------
		frm.fields_dict['buying_cost_center'].get_query = function(doc) {
			return {
				filters:{ 'group_or_ledger': "Ledger" }
			}
		}


		// Sales Cost Center
		// -----------------------------
		frm.fields_dict['selling_cost_center'].get_query = function(doc) {
			return {
				filters:{ 'group_or_ledger': "Ledger" }
			}
		}


		frm.fields_dict['taxes'].grid.get_field("tax_type").get_query = function(doc, cdt, cdn) {
			return {
				filters: [
					['Account', 'account_type', 'in',
						'Tax, Chargeable, Income Account, Expense Account'],
					['Account', 'docstatus', '!=', 2]
				]
			}
		}

		frm.fields_dict['item_group'].get_query = function(doc,cdt,cdn) {
			return {
				filters: [
					['Item Group', 'docstatus', '!=', 2]
				]
			}
		}

		frm.fields_dict.customer_items.grid.get_field("customer_name").get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.customer_query" }
		}

		frm.fields_dict.supplier_items.grid.get_field("supplier").get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.supplier_query" }
		}

	},

	toggle_reqd: function(frm) {
		frm.toggle_reqd("default_warehouse", frm.doc.is_stock_item==="Yes");
	},

	make_dashboard: function(frm) {
		frm.dashboard.reset();
		if(frm.doc.__islocal)
			return;
	},

	edit_prices_button: function(frm) {
		frm.add_custom_button(__("Add / Edit Prices"), function() {
			frappe.set_route("Report", "Item Price", {"item_code": frm.doc.name});
		}, "icon-money", "btn-default");
	},

	weight_to_validate: function(frm){
		if((frm.doc.nett_weight || frm.doc.gross_weight) && !frm.doc.weight_uom) {
			msgprint(__('Weight is mentioned,\nPlease mention "Weight UOM" too'));
			validated = 0;
		}
	},

});
