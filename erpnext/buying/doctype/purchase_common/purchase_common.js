// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname

wn.provide("erpnext.buying");
wn.require("assets/erpnext/js/transaction.js");
{% include "public/js/controllers/accounts.js" %}

erpnext.buying.BuyingController = erpnext.TransactionController.extend({
	onload: function() {
		this.setup_queries();
		this._super();
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
		
		this.frm.set_query("item_code", this.frm.cscript.fname, function() {
			if(me.frm.doc.is_subcontracted == "Yes") {
				 return{
					query: "erpnext.controllers.queries.item_query",
					filters:{ 'is_sub_contracted_item': 'Yes' }
				}
			} else {
				return{
					query: "erpnext.controllers.queries.item_query",
					filters: { 'is_purchase_item': 'Yes' }
				}				
			}
		});
	},
	
	refresh: function(doc) {
		this.frm.toggle_display("supplier_name", 
			(this.supplier_name && this.frm.doc.supplier_name!==this.frm.doc.supplier));
		this._super();
	},
	
	supplier: function() {
		erpnext.utils.get_party_details(this.frm);
	},
	
	supplier_address: function() {
		erpnext.utils.get_address_display(this.frm);
	},
	
	contact_person: function() { 
		this.supplier_address();
	},
	
	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code) {
			if(!this.validate_company_and_party("supplier")) {
				cur_frm.fields_dict[me.frm.cscript.fname].grid.grid_rows[item.idx - 1].remove();
			} else {
				return this.frm.call({
					method: "erpnext.buying.utils.get_item_details",
					child: item,
					args: {
						args: {
							item_code: item.item_code,
							warehouse: item.warehouse,
							doctype: me.frm.doc.doctype,
							docname: me.frm.doc.name,
							supplier: me.frm.doc.supplier,
							conversion_rate: me.frm.doc.conversion_rate,
							buying_price_list: me.frm.doc.buying_price_list,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							is_subcontracted: me.frm.doc.is_subcontracted,
							company: me.frm.doc.company,
							currency: me.frm.doc.currency,
							transaction_date: me.frm.doc.transaction_date
						}
					},
					callback: function(r) {
						if(!r.exc) {
							me.frm.script_manager.trigger("price_list_rate", cdt, cdn);
						}
					}
				});
			}
		}
	},
	
	buying_price_list: function() {
		this.get_price_list_currency("Buying");
	},
	
	price_list_rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		wn.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);
		
		item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0),
			precision("rate", item));
		
		this.calculate_taxes_and_totals();
	},
	
	discount_percentage: function(doc, cdt, cdn) {
		this.price_list_rate(doc, cdt, cdn);
	},
	
	rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		wn.model.round_floats_in(item, ["rate", "discount_percentage"]);
		
		if(item.price_list_rate) {
			item.discount_percentage = flt((1 - item.rate / item.price_list_rate) * 100.0,
				precision("discount_percentage", item));
		} else {
			item.discount_percentage = 0.0;
		}
		
		this.calculate_taxes_and_totals();
	},
	
	uom: function(doc, cdt, cdn) {
		var me = this;
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code && item.uom) {
			return this.frm.call({
				method: "erpnext.buying.utils.get_conversion_factor",
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
		this._super(doc, cdt, cdn);
		this.conversion_factor(doc, cdt, cdn);
	},
	
	conversion_factor: function(doc, cdt, cdn) {
		if(wn.meta.get_docfield(cdt, "stock_qty", cdn)) {
			var item = wn.model.get_doc(cdt, cdn);
			wn.model.round_floats_in(item, ["qty", "conversion_factor"]);
			item.stock_qty = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
			refresh_field("stock_qty", item.name, item.parentfield);
		}
	},
	
	warehouse: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code && item.warehouse) {
			return this.frm.call({
				method: "erpnext.buying.utils.get_projected_qty",
				child: item,
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse
				}
			});
		}
	},
	
	project_name: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(item.project_name) {
			$.each(wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name, {parentfield: this.fname}),
				function(i, other_item) { 
					if(!other_item.project_name) {
						other_item.project_name = item.project_name;
						refresh_field("project_name", other_item.name, other_item.parentfield);
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
	
	calculate_taxes_and_totals: function() {
		this._super();
		this.calculate_total_advance("Purchase Invoice", "advance_allocation_details");
		this.frm.refresh_fields();
	},
	
	calculate_item_values: function() {
		var me = this;
		
		$.each(this.frm.item_doclist, function(i, item) {
			wn.model.round_floats_in(item);
			item.import_amount = flt(item.rate * item.qty, precision("import_amount", item));
			item.item_tax_amount = 0.0;
			
			me._set_in_company_currency(item, "price_list_rate", "base_price_list_rate");
			me._set_in_company_currency(item, "rate", "base_rate");
			me._set_in_company_currency(item, "import_amount", "amount");
		});
		
	},
	
	calculate_net_total: function() {
		var me = this;

		this.frm.doc.net_total = this.frm.doc.net_total_import = 0.0;
		$.each(this.frm.item_doclist, function(i, item) {
			me.frm.doc.net_total += item.amount;
			me.frm.doc.net_total_import += item.import_amount;
		});
		
		wn.model.round_floats_in(this.frm.doc, ["net_total", "net_total_import"]);
	},
	
	calculate_totals: function() {
		var tax_count = this.frm.tax_doclist.length;
		this.frm.doc.grand_total = flt(tax_count ? 
			this.frm.tax_doclist[tax_count - 1].total : this.frm.doc.net_total,
			precision("grand_total"));
		this.frm.doc.grand_total_import = flt(this.frm.doc.grand_total / 
			this.frm.doc.conversion_rate, precision("grand_total_import"));
			
		this.frm.doc.total_tax = flt(this.frm.doc.grand_total - this.frm.doc.net_total,
			precision("total_tax"));
		
		// rounded totals
		if(wn.meta.get_docfield(this.frm.doc.doctype, "rounded_total", this.frm.doc.name)) {
			this.frm.doc.rounded_total = Math.round(this.frm.doc.grand_total);
		}
		
		if(wn.meta.get_docfield(this.frm.doc.doctype, "rounded_total_import", this.frm.doc.name)) {
			this.frm.doc.rounded_total_import = Math.round(this.frm.doc.grand_total_import);
		}
		
		// other charges added/deducted
		this.frm.doc.other_charges_added = 0.0
		this.frm.doc.other_charges_deducted = 0.0
		if(tax_count) {
			this.frm.doc.other_charges_added = wn.utils.sum($.map(this.frm.tax_doclist, 
				function(tax) { return (tax.add_deduct_tax == "Add" 
					&& in_list(["Valuation and Total", "Total"], tax.category)) ? 
					tax.tax_amount : 0.0; }));
		
			this.frm.doc.other_charges_deducted = wn.utils.sum($.map(this.frm.tax_doclist, 
				function(tax) { return (tax.add_deduct_tax == "Deduct" 
					&& in_list(["Valuation and Total", "Total"], tax.category)) ? 
					tax.tax_amount : 0.0; }));
			
			wn.model.round_floats_in(this.frm.doc,
				["other_charges_added", "other_charges_deducted"]);
		}
		this.frm.doc.other_charges_added_import = flt(this.frm.doc.other_charges_added /
			this.frm.doc.conversion_rate, precision("other_charges_added_import"));
		this.frm.doc.other_charges_deducted_import = flt(this.frm.doc.other_charges_deducted / 
			this.frm.doc.conversion_rate, precision("other_charges_deducted_import"));
	},
	
	_cleanup: function() {
		this._super();
		this.frm.doc.in_words = this.frm.doc.in_words_import = "";
		
		if(this.frm.item_doclist.length) {
			if(!wn.meta.get_docfield(this.frm.item_doclist[0].doctype, "item_tax_amount", this.frm.doctype)) {
				$.each(this.frm.item_doclist, function(i, item) {
					delete item["item_tax_amount"];
				});
			}
		}

		if(this.frm.tax_doclist.length) {
			if(!wn.meta.get_docfield(this.frm.tax_doclist[0].doctype, "tax_amount_after_discount_amount", this.frm.doctype)) {
				$.each(this.frm.tax_doclist, function(i, tax) {
					delete tax["tax_amount_after_discount_amount"];
				});
			}
		}
	},
	
	calculate_outstanding_amount: function() {
		if(this.frm.doc.doctype == "Purchase Invoice" && this.frm.doc.docstatus < 2) {
			wn.model.round_floats_in(this.frm.doc, ["grand_total", "total_advance", "write_off_amount"]);
			this.frm.doc.total_amount_to_pay = flt(this.frm.doc.grand_total - this.frm.doc.write_off_amount,
				precision("total_amount_to_pay"));
			this.frm.doc.outstanding_amount = flt(this.frm.doc.total_amount_to_pay - this.frm.doc.total_advance,
				precision("outstanding_amount"));
		}
	},
	
	set_item_tax_amount: function(item, tax, current_tax_amount) {
		// item_tax_amount is the total tax amount applied on that item
		// stored for valuation 
		// 
		// TODO: rename item_tax_amount to valuation_tax_amount
		if(["Valuation", "Valuation and Total"].indexOf(tax.category) != -1 &&
			wn.meta.get_docfield(item.doctype, "item_tax_amount", item.parent || item.name)) {
				// accumulate only if tax is for Valuation / Valuation and Total
				item.item_tax_amount += flt(current_tax_amount, precision("item_tax_amount", item));
		}
	},
	
	change_form_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};
		
		var setup_field_label_map = function(fields_list, currency) {
			$.each(fields_list, function(i, fname) {
				var docfield = wn.meta.docfield_map[me.frm.doc.doctype][fname];
				if(docfield) {
					var label = wn._(docfield.label || "").replace(/\([^\)]*\)/g, "");
					field_label_map[fname] = label.trim() + " (" + currency + ")";
				}
			});
		};
		
		
		setup_field_label_map(["net_total", "total_tax", "grand_total", "in_words",
			"other_charges_added", "other_charges_deducted", 
			"outstanding_amount", "total_advance", "total_amount_to_pay", "rounded_total"],
			company_currency);
		
		setup_field_label_map(["net_total_import", "grand_total_import", "in_words_import",
			"other_charges_added_import", "other_charges_deducted_import"], this.frm.doc.currency);
		
		cur_frm.set_df_property("conversion_rate", "description", "1 " + this.frm.doc.currency 
			+ " = [?] " + company_currency);
		
		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			cur_frm.set_df_property("plc_conversion_rate", "description", "1 " + this.frm.doc.price_list_currency 
				+ " = [?] " + company_currency);
		}
		
		// toggle fields
		this.frm.toggle_display(["conversion_rate", "net_total", "grand_total", 
			"in_words", "other_charges_added", "other_charges_deducted"],
			this.frm.doc.currency !== company_currency);
		
		this.frm.toggle_display(["plc_conversion_rate", "price_list_currency"], 
			this.frm.doc.price_list_currency !== company_currency);		

		// set labels
		$.each(field_label_map, function(fname, label) {
			me.frm.fields_dict[fname].set_label(label);
		});

	},
	
	change_grid_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};
		
		var setup_field_label_map = function(fields_list, currency, parentfield) {
			var grid_doctype = me.frm.fields_dict[parentfield].grid.doctype;
			$.each(fields_list, function(i, fname) {
				var docfield = wn.meta.docfield_map[grid_doctype][fname];
				if(docfield) {
					var label = wn._(docfield.label || "").replace(/\([^\)]*\)/g, "");
					field_label_map[grid_doctype + "-" + fname] = 
						label.trim() + " (" + currency + ")";
				}
			});
		};
		
		setup_field_label_map(["base_rate", "base_price_list_rate", "amount", "base_rate"],
			company_currency, this.fname);
		
		setup_field_label_map(["rate", "price_list_rate", "import_amount"],
			this.frm.doc.currency, this.fname);
		
		if(this.frm.fields_dict[this.other_fname]) {
			setup_field_label_map(["tax_amount", "total"], company_currency, this.other_fname);
		}
		
		if(this.frm.fields_dict["advance_allocation_details"]) {
			setup_field_label_map(["advance_amount", "allocated_amount"], company_currency,
				"advance_allocation_details");
		}
		
		// toggle columns
		var item_grid = this.frm.fields_dict[this.fname].grid;
		var fieldnames = $.map(["base_rate", "base_price_list_rate", "amount", "base_rate"], function(fname) {
			return wn.meta.get_docfield(item_grid.doctype, fname, me.frm.docname) ? fname : null;
		});
		
		item_grid.set_column_disp(fieldnames, this.frm.doc.currency != company_currency);
		
		// set labels
		var $wrapper = $(this.frm.wrapper);
		$.each(field_label_map, function(fname, label) {
			$wrapper.find('[data-grid-fieldname="'+fname+'"]').text(label);
		});
	}
});

var tname = cur_frm.cscript.tname;
var fname = cur_frm.cscript.fname;
