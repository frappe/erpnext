// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");

cur_frm.cscript.tax_table = "Purchase Taxes and Charges";

{% include 'erpnext/accounts/doctype/purchase_taxes_and_charges_template/purchase_taxes_and_charges_template.js' %}

cur_frm.email_field = "contact_email";

erpnext.buying.BuyingController = erpnext.TransactionController.extend({
	setup: function() {
		this._super();
	},

	onload: function() {
		this.setup_queries();
		this._super();

		if(this.frm.get_field('shipping_address')) {
			this.frm.set_query("shipping_address", function(){
				if(me.frm.doc.customer){
					return{
						filters:{
							"customer": me.frm.doc.customer
						}
					}
				}
				else{
					return{
						filters:{
							"is_your_company_address": 1,
							"company": me.frm.doc.company
						}
					}
				}
			});
		}
	},

	setup_queries: function() {
		var me = this;

		if(this.frm.fields_dict.buying_price_list) {
			this.frm.set_query("buying_price_list", function() {
				return{
					filters: { 'buying': 1 }
				}
			});
		}

		$.each([["supplier", "supplier"],
			["contact_person", "supplier_filter"],
			["supplier_address", "supplier_filter"]],
			function(i, opts) {
				if(me.frm.fields_dict[opts[0]])
					me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});

		if(this.frm.fields_dict.supplier) {
			this.frm.set_query("supplier", function() {
				return{	query: "erpnext.controllers.queries.supplier_query" }});
		}

		this.frm.set_query("item_code", "items", function() {
			if(me.frm.doc.is_subcontracted == "Yes") {
				return{
					query: "erpnext.controllers.queries.item_query",
					filters:{ 'is_sub_contracted_item': 1 }
				}
			} else {
				return{
					query: "erpnext.controllers.queries.item_query",
					filters: {'is_purchase_item': 1}
				}
			}
		});
	},

	refresh: function(doc) {
		this.frm.toggle_display("supplier_name",
			(this.frm.doc.supplier_name && this.frm.doc.supplier_name!==this.frm.doc.supplier));

		if(this.frm.docstatus==0 &&
			(this.frm.doctype==="Purchase Order" || this.frm.doctype==="Material Request")) {
			this.set_from_product_bundle();
		}

		this._super();
	},

	supplier: function() {
		var me = this;
		erpnext.utils.get_party_details(this.frm, null, null, function(){me.apply_pricing_rule()});
	},

	supplier_address: function() {
		erpnext.utils.get_address_display(this.frm);
	},

	buying_price_list: function() {
		this.apply_price_list();
	},

	price_list_rate: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);

		item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0),
			precision("rate", item));

		this.calculate_taxes_and_totals();
	},

	discount_percentage: function(doc, cdt, cdn) {
		this.price_list_rate(doc, cdt, cdn);
	},

	uom: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code && item.uom) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				child: item,
				args: {
					item_code: item.item_code,
					uom: item.uom
				},
				callback: function(r) {
					if(!r.exc) {
						me.conversion_factor(me.frm.doc, cdt, cdn);
					}
				}
			});
		}
	},

	qty: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if ((doc.doctype == "Purchase Receipt") || (doc.doctype == "Purchase Invoice" && doc.update_stock)) {
			frappe.model.round_floats_in(item, ["qty", "received_qty"]);
			if(!(item.received_qty || item.rejected_qty) && item.qty) {
				item.received_qty = item.qty;
			}

			frappe.model.round_floats_in(item, ["qty", "received_qty"]);
			item.rejected_qty = flt(item.received_qty - item.qty, precision("rejected_qty", item));
		}

		this._super(doc, cdt, cdn);
		this.conversion_factor(doc, cdt, cdn);

	},

	received_qty: function(doc, cdt, cdn) {
		this.calculate_accepted_qty(doc, cdt, cdn)
	},

	rejected_qty: function(doc, cdt, cdn) {
		this.calculate_accepted_qty(doc, cdt, cdn)
	},

	calculate_accepted_qty: function(doc, cdt, cdn){
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["received_qty", "rejected_qty"]);

		item.qty = flt(item.received_qty - item.rejected_qty, precision("qty", item));
		this.qty(doc, cdt, cdn);
	},

	conversion_factor: function(doc, cdt, cdn) {
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
			var item = frappe.get_doc(cdt, cdn);
			frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
			item.stock_qty = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
			refresh_field("stock_qty", item.name, item.parentfield);
		}
	},

	warehouse: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code && item.warehouse) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_projected_qty",
				child: item,
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse
				}
			});
		}
	},

	project: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if(item.project) {
			$.each(this.frm.doc["items"] || [],
				function(i, other_item) {
					if(!other_item.project) {
						other_item.project = item.project;
						refresh_field("project", other_item.name, other_item.parentfield);
					}
				});
		}
	},

	category: function(doc, cdt, cdn) {
		// should be the category field of tax table
		if(cdt != doc.doctype) {
			this.calculate_taxes_and_totals();
		}
	},
	add_deduct_tax: function(doc, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},

	set_from_product_bundle: function() {
		var me = this;
		this.frm.add_custom_button(__("Product Bundle"), function() {
			erpnext.buying.get_items_from_product_bundle(me.frm);
		}, __("Get items from"));
	},

	shipping_address: function(){
		var me = this;
		erpnext.utils.get_address_display(this.frm, "shipping_address",
			"shipping_address_display", is_your_company_address=true)
	},

	tc_name: function() {
		this.get_terms();
	}
});

cur_frm.add_fetch('project', 'cost_center', 'cost_center');

erpnext.buying.get_default_bom = function(frm) {
	$.each(frm.doc["items"] || [], function(i, d) {
		if (d.item_code && d.bom === "") {
			return frappe.call({
				type: "GET",
				method: "erpnext.stock.get_item_details.get_default_bom",
				args: {
					"item_code": d.item_code,
				},
				callback: function(r) {
					if(r) {
						frappe.model.set_value(d.doctype, d.name, "bom", r.message);
					}
				}
			})
		}
	});
}

erpnext.buying.get_items_from_product_bundle = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Product Bundle"),
		fields: [
			{
				"fieldtype": "Link",
				"label": __("Product Bundle"),
				"fieldname": "product_bundle",
				"options":"Product Bundle",
				"reqd": 1
			},
			{
				"fieldtype": "Currency",
				"label": __("Quantity"),
				"fieldname": "quantity",
				"reqd": 1,
				"default": 1
			},
			{
				"fieldtype": "Button",
				"label": __("Get Items"),
				"fieldname": "get_items",
				"cssClass": "btn-primary"
			}
		]
	});

	dialog.fields_dict.get_items.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		dialog.hide();
		return frappe.call({
			type: "GET",
			method: "erpnext.stock.doctype.packed_item.packed_item.get_items_from_product_bundle",
			args: {
				args: {
					item_code: args.product_bundle,
					quantity: args.quantity,
					parenttype: frm.doc.doctype,
					parent: frm.doc.name,
					supplier: frm.doc.supplier,
					currency: frm.doc.currency,
					conversion_rate: frm.doc.conversion_rate,
					price_list: frm.doc.buying_price_list,
					price_list_currency: frm.doc.price_list_currency,
					plc_conversion_rate: frm.doc.plc_conversion_rate,
					company: frm.doc.company,
					is_subcontracted: frm.doc.is_subcontracted,
					transaction_date: frm.doc.transaction_date || frm.doc.posting_date,
					ignore_pricing_rule: frm.doc.ignore_pricing_rule
				}
			},
			freeze: true,
			callback: function(r) {
				if(!r.exc && r.message) {
					for ( var i=0; i< r.message.length; i++ ) {
						var d = frm.add_child("items");
						var item = r.message[i];
						for ( var key in  item) {
							if ( !is_null(item[key]) ) {
								d[key] = item[key];
							}
						}
						if(frappe.meta.get_docfield(d.doctype, "price_list_rate", d.name)) {
							frm.script_manager.trigger("price_list_rate", d.doctype, d.name);
						}
					}
					frm.refresh_field("items");
				}
			}
		})
	});
	dialog.show();
}
