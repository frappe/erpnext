// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname
// cur_frm.cscript.other_fname - wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js'); fieldname
// cur_frm.cscript.sales_team_fname - Sales Team fieldname

wn.provide("erpnext.selling");
wn.require("app/js/transaction.js");
wn.require("app/js/controllers/accounts.js");

erpnext.selling.SellingController = erpnext.TransactionController.extend({
	onload: function() {
		this._super();
		this.toggle_rounded_total();
		this.setup_queries();
		this.toggle_editable_price_list_rate();
	},
	
	setup_queries: function() {
		var me = this;
		
		this.frm.add_fetch("sales_partner", "commission_rate", "commission_rate");
		
		$.each([["customer_address", "customer_filter"], 
			["shipping_address_name", "customer_filter"],
			["contact_person", "customer_filter"], 
			["customer", "customer"], 
			["lead", "lead"]], 
			function(i, opts) {
				if(me.frm.fields_dict[opts[0]]) 
					me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});
		
		if(this.frm.fields_dict.charge) {
			this.frm.set_query("charge", function() {
				return {
					filters: [
						['Sales Taxes and Charges Master', 'company', '=', me.frm.doc.company],
						['Sales Taxes and Charges Master', 'docstatus', '!=', 2]
					]
				}
			});
		}

		if(this.frm.fields_dict.selling_price_list) {
			this.frm.set_query("selling_price_list", function() {
				return { filters: { buying_or_selling: "Selling" } };
			});
		}
			
		if(!this.fname) {
			return;
		}
		
		if(this.frm.fields_dict[this.fname].grid.get_field('item_code')) {
			this.frm.set_query("item_code", this.fname, function() {
				return {
					query: "controllers.queries.item_query",
					filters: (me.frm.doc.order_type === "Maintenance" ?
						{'is_service_item': 'Yes'}:
						{'is_sales_item': 'Yes'	})
				}
			});
		}
		
		if(this.frm.fields_dict[this.fname].grid.get_field('batch_no')) {
			this.frm.set_query("batch_no", this.fname, function(doc, cdt, cdn) {
				var item = wn.model.get_doc(cdt, cdn);
				if(!item.item_code) {
					wn.throw(wn._("Please enter Item Code to get batch no"));
				} else {
					filters = {
						'item_code': item.item_code,
						'posting_date': me.frm.doc.posting_date,
					}
					if(item.warehouse) filters["warehouse"] = item.warehouse
					
					return {
						query : "controllers.queries.get_batch_no",
						filters: filters
					}
				}
			});
		}
		
		if(this.frm.fields_dict.sales_team && this.frm.fields_dict.sales_team.grid.get_field("sales_person")) {
			this.frm.set_query("sales_person", "sales_team", erpnext.queries.not_a_group_filter);
		}
	},
	
	refresh: function() {
		this._super();
		this.frm.toggle_display("customer_name", 
			(this.customer_name && this.frm.doc.customer_name!==this.frm.doc.customer));
		if(this.frm.fields_dict.packing_details) {
			var packing_list_exists = this.frm.get_doclist({parentfield: "packing_details"}).length;
			this.frm.toggle_display("packing_list", packing_list_exists ? true : false);
		}
	},
	
	customer: function() {
		var me = this;
		if(this.frm.doc.customer || this.frm.doc.debit_to) {
			if(!this.frm.doc.company) {
				this.frm.set_value("customer", null);
				msgprint(wn._("Please specify Company"));
			} else {
				var selling_price_list = this.frm.doc.selling_price_list;
				return this.frm.call({
					doc: this.frm.doc,
					method: "set_customer_defaults",
					freeze: true,
					callback: function(r) {
						if(!r.exc) {
							(me.frm.doc.selling_price_list !== selling_price_list) ? 
								me.selling_price_list() :
								me.price_list_currency();
						}
					}
				});
			}
		}
	},
	
	customer_address: function() {
		var me = this;
		if(this.frm.doc.customer) {
			return this.frm.call({
				doc: this.frm.doc,
				args: {
					customer: this.frm.doc.customer, 
					address: this.frm.doc.customer_address, 
					contact: this.frm.doc.contact_person
				},
				method: "set_customer_address",
				freeze: true,
			});
		}
	},
	
	contact_person: function() {
		this.customer_address();
	},
	
	barcode: function(doc, cdt, cdn) {
		this.item_code(doc, cdt, cdn);
	},
	
	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code || item.barcode || item.serial_no) {
			if(!this.validate_company_and_party("customer")) {
				cur_frm.fields_dict[me.frm.cscript.fname].grid.grid_rows[item.idx - 1].remove();
			} else {
				return this.frm.call({
					method: "selling.utils.get_item_details",
					child: item,
					args: {
						args: {
							item_code: item.item_code,
							barcode: item.barcode,
							serial_no: item.serial_no,
							warehouse: item.warehouse,
							doctype: me.frm.doc.doctype,
							parentfield: item.parentfield,
							customer: me.frm.doc.customer,
							currency: me.frm.doc.currency,
							conversion_rate: me.frm.doc.conversion_rate,
							selling_price_list: me.frm.doc.selling_price_list,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							company: me.frm.doc.company,
							order_type: me.frm.doc.order_type,
							is_pos: cint(me.frm.doc.is_pos),
						}
					},
					callback: function(r) {
						if(!r.exc) {
							me.frm.script_manager.trigger("ref_rate", cdt, cdn);
						}
					}
				});
			}
		}
	},
	
	selling_price_list: function() {
		this.get_price_list_currency("Selling");
	},
	
	ref_rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		wn.model.round_floats_in(item, ["ref_rate", "adj_rate"]);
		
		item.export_rate = flt(item.ref_rate * (1 - item.adj_rate / 100.0),
			precision("export_rate", item));
		
		this.calculate_taxes_and_totals();
	},
	
	adj_rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(!item.ref_rate) {
			item.adj_rate = 0.0;
		} else {
			this.ref_rate(doc, cdt, cdn);
		}
	},
	
	export_rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		wn.model.round_floats_in(item, ["export_rate", "ref_rate"]);
		
		if(item.ref_rate) {
			item.adj_rate = flt((1 - item.export_rate / item.ref_rate) * 100.0,
				precision("adj_rate", item));
		} else {
			item.adj_rate = 0.0;
		}
		
		this.calculate_taxes_and_totals();
	},
	
	commission_rate: function() {
		this.calculate_commission();
		refresh_field("total_commission");
	},
	
	total_commission: function() {
		if(this.frm.doc.net_total) {
			wn.model.round_floats_in(this.frm.doc, ["net_total", "total_commission"]);
			
			if(this.frm.doc.net_total < this.frm.doc.total_commission) {
				var msg = (wn._("[Error]") + " " + 
					wn._(wn.meta.get_label(this.frm.doc.doctype, "total_commission", 
						this.frm.doc.name)) + " > " + 
					wn._(wn.meta.get_label(this.frm.doc.doctype, "net_total", this.frm.doc.name)));
				msgprint(msg);
				throw msg;
			}
		
			this.frm.set_value("commission_rate", 
				flt(this.frm.doc.total_commission * 100.0 / this.frm.doc.net_total));
		}
	},
	
	allocated_percentage: function(doc, cdt, cdn) {
		var sales_person = wn.model.get_doc(cdt, cdn);
		
		if(sales_person.allocated_percentage) {
			sales_person.allocated_percentage = flt(sales_person.allocated_percentage,
				precision("allocated_percentage", sales_person));
			sales_person.allocated_amount = flt(this.frm.doc.net_total *
				sales_person.allocated_percentage / 100.0, 
				precision("allocated_amount", sales_person));

			refresh_field(["allocated_percentage", "allocated_amount"], sales_person.name,
				sales_person.parentfield);
		}
	},
	
	warehouse: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code && item.warehouse) {
			return this.frm.call({
				method: "selling.utils.get_available_qty",
				child: item,
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse,
				},
			});
		}
	},
	
	toggle_rounded_total: function() {
		var me = this;
		if(cint(wn.defaults.get_global_default("disable_rounded_total"))) {
			$.each(["rounded_total", "rounded_total_export"], function(i, fieldname) {
				me.frm.set_df_property(fieldname, "print_hide", 1);
				me.frm.toggle_display(fieldname, false);
			});
		}
	},
	
	toggle_editable_price_list_rate: function() {
		var df = wn.meta.get_docfield(this.tname, "ref_rate", this.frm.doc.name);
		var editable_price_list_rate = cint(wn.defaults.get_default("editable_price_list_rate"));
		
		if(df && editable_price_list_rate) {
			df.read_only = 0;
		}
	},
	
	calculate_taxes_and_totals: function() {
		this._super();
		this.calculate_total_advance("Sales Invoice", "advance_adjustment_details");
		this.calculate_commission();
		this.calculate_contribution();

		// TODO check for custom_recalc in custom scripts of server
		
		this.frm.refresh_fields();
	},
	
	calculate_item_values: function() {
		var me = this;
		$.each(this.frm.item_doclist, function(i, item) {
			wn.model.round_floats_in(item);
			item.export_amount = flt(item.export_rate * item.qty, precision("export_amount", item));
			
			me._set_in_company_currency(item, "ref_rate", "base_ref_rate");
			me._set_in_company_currency(item, "export_rate", "basic_rate");
			me._set_in_company_currency(item, "export_amount", "amount");
		});
		
	},
	
	determine_exclusive_rate: function() {
		var me = this;
		$.each(me.frm.item_doclist, function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			var cumulated_tax_fraction = 0.0;
			
			$.each(me.frm.tax_doclist, function(i, tax) {
				tax.tax_fraction_for_current_item = me.get_current_tax_fraction(tax, item_tax_map);
				
				if(i==0) {
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item;
				} else {
					tax.grand_total_fraction_for_current_item = 
						me.frm.tax_doclist[i-1].grand_total_fraction_for_current_item +
						tax.tax_fraction_for_current_item;
				}
				
				cumulated_tax_fraction += tax.tax_fraction_for_current_item;
			});
			
			if(cumulated_tax_fraction) {
				item.amount = flt(
					(item.export_amount * me.frm.doc.conversion_rate) / (1 + cumulated_tax_fraction),
					precision("amount", item));
					
				item.basic_rate = flt(item.amount / item.qty, precision("basic_rate", item));
				
				if(item.adj_rate == 100) {
					item.base_ref_rate = item.basic_rate;
					item.basic_rate = 0.0;
				} else {
					item.base_ref_rate = flt(item.basic_rate / (1 - item.adj_rate / 100.0),
						precision("base_ref_rate", item));
				}
			}
		});
	},
	
	get_current_tax_fraction: function(tax, item_tax_map) {
		// Get tax fraction for calculating tax exclusive amount
		// from tax inclusive amount
		var current_tax_fraction = 0.0;
		
		if(cint(tax.included_in_print_rate)) {
			var tax_rate = this._get_tax_rate(tax, item_tax_map);
			
			if(tax.charge_type == "On Net Total") {
				current_tax_fraction = (tax_rate / 100.0);
				
			} else if(tax.charge_type == "On Previous Row Amount") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.tax_doclist[cint(tax.row_id) - 1].tax_fraction_for_current_item;
				
			} else if(tax.charge_type == "On Previous Row Total") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.tax_doclist[cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			}
		}
		
		return current_tax_fraction;
	},
	
	calculate_net_total: function() {
		var me = this;

		this.frm.doc.net_total = this.frm.doc.net_total_export = 0.0;
		$.each(this.frm.item_doclist, function(i, item) {
			me.frm.doc.net_total += item.amount;
			me.frm.doc.net_total_export += item.export_amount;
		});
		
		wn.model.round_floats_in(this.frm.doc, ["net_total", "net_total_export"]);
	},
	
	calculate_totals: function() {
		var tax_count = this.frm.tax_doclist.length;
		this.frm.doc.grand_total = flt(
			tax_count ? this.frm.tax_doclist[tax_count - 1].total : this.frm.doc.net_total,
			precision("grand_total"));
		this.frm.doc.grand_total_export = flt(this.frm.doc.grand_total / this.frm.doc.conversion_rate,
			precision("grand_total_export"));
			
		this.frm.doc.other_charges_total = flt(this.frm.doc.grand_total - this.frm.doc.net_total,
			precision("other_charges_total"));
		this.frm.doc.other_charges_total_export = flt(
			this.frm.doc.grand_total_export - this.frm.doc.net_total_export,
			precision("other_charges_total_export"));
			
		this.frm.doc.rounded_total = Math.round(this.frm.doc.grand_total);
		this.frm.doc.rounded_total_export = Math.round(this.frm.doc.grand_total_export);
	},
	
	calculate_outstanding_amount: function() {
		// NOTE: 
		// paid_amount and write_off_amount is only for POS Invoice
		// total_advance is only for non POS Invoice
		if(this.frm.doc.doctype == "Sales Invoice" && this.frm.doc.docstatus==0) {
			wn.model.round_floats_in(this.frm.doc, ["grand_total", "total_advance", "write_off_amount",
				"paid_amount"]);
			var total_amount_to_pay = this.frm.doc.grand_total - this.frm.doc.write_off_amount - this.frm.doc.total_advance;
			this.frm.doc.paid_amount = this.frm.doc.is_pos? flt(total_amount_to_pay): 0.0;

			this.frm.doc.outstanding_amount = flt(total_amount_to_pay - this.frm.doc.paid_amount, 
				precision("outstanding_amount"));
		}
	},
	
	calculate_commission: function() {
		if(this.frm.fields_dict.commission_rate) {
			if(this.frm.doc.commission_rate > 100) {
				var msg = wn._(wn.meta.get_label(this.frm.doc.doctype, "commission_rate", this.frm.doc.name)) +
					" " + wn._("cannot be greater than 100");
				msgprint(msg);
				throw msg;
			}
		
			this.frm.doc.total_commission = flt(this.frm.doc.net_total * this.frm.doc.commission_rate / 100.0,
				precision("total_commission"));
		}
	},
	
	calculate_contribution: function() {
		var me = this;
		$.each(wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name, 
			{parentfield: "sales_team"}), function(i, sales_person) {
				wn.model.round_floats_in(sales_person);
				if(sales_person.allocated_percentage) {
					sales_person.allocated_amount = flt(
						me.frm.doc.net_total * sales_person.allocated_percentage / 100.0,
						precision("allocated_amount", sales_person));
				}
			});
	},
	
	_cleanup: function() {
		this._super();
		this.frm.doc.in_words = this.frm.doc.in_words_export = "";
	},

	show_item_wise_taxes: function() {
		if(this.frm.fields_dict.other_charges_calculation) {
			$(this.get_item_wise_taxes_html())
				.appendTo($(this.frm.fields_dict.other_charges_calculation.wrapper).empty());
		}
	},
	
	charge: function() {
		var me = this;
		if(this.frm.doc.charge) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "get_other_charges",
				callback: function(r) {
					if(!r.exc) {
						me.calculate_taxes_and_totals();
					}
				}
			});
		}
	},
	
	shipping_rule: function() {
		var me = this;
		if(this.frm.doc.shipping_rule) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "apply_shipping_rule",
				callback: function(r) {
					if(!r.exc) {
						me.calculate_taxes_and_totals();
					}
				}
			})
		}
	},
	
	set_dynamic_labels: function() {
		this._super();
		set_sales_bom_help(this.frm.doc);
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
		
		setup_field_label_map(["net_total", "other_charges_total", "grand_total", 
			"rounded_total", "in_words",
			"outstanding_amount", "total_advance", "paid_amount", "write_off_amount"],
			company_currency);
		
		setup_field_label_map(["net_total_export", "other_charges_total_export", "grand_total_export", 
			"rounded_total_export", "in_words_export"], this.frm.doc.currency);
		
		cur_frm.set_df_property("conversion_rate", "description", "1 " + this.frm.doc.currency 
			+ " = [?] " + company_currency)
		
		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			cur_frm.set_df_property("plc_conversion_rate", "description", "1 " + this.frm.doc.price_list_currency 
				+ " = [?] " + company_currency)
		}
		
		// toggle fields
		this.frm.toggle_display(["conversion_rate", "net_total", "other_charges_total", 
			"grand_total", "rounded_total", "in_words"],
			this.frm.doc.currency != company_currency);
			
		this.frm.toggle_display(["plc_conversion_rate", "price_list_currency"], 
			this.frm.doc.price_list_currency != company_currency);
		
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
		}
		
		setup_field_label_map(["basic_rate", "base_ref_rate", "amount"],
			company_currency, this.fname);
		
		setup_field_label_map(["export_rate", "ref_rate", "export_amount"],
			this.frm.doc.currency, this.fname);
		
		setup_field_label_map(["tax_amount", "total"], company_currency, "other_charges");
		
		if(this.frm.fields_dict["advance_allocation_details"]) {
			setup_field_label_map(["advance_amount", "allocated_amount"], company_currency,
				"advance_allocation_details");
		}
		
		// toggle columns
		var item_grid = this.frm.fields_dict[this.fname].grid;
		var show = (this.frm.doc.currency != company_currency) || 
			(wn.model.get_doclist(cur_frm.doctype, cur_frm.docname, 
				{parentfield: "other_charges", included_in_print_rate: 1}).length);
		
		$.each(["basic_rate", "base_ref_rate", "amount"], function(i, fname) {
			if(wn.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, show);
		});
		
		// set labels
		var $wrapper = $(this.frm.wrapper);
		$.each(field_label_map, function(fname, label) {
			fname = fname.split("-");
			var df = wn.meta.get_docfield(fname[0], fname[1], me.frm.doc.name);
			if(df) df.label = label;
		});
	},
	
	shipping_address_name: function () {
		var me = this;
		if(this.frm.doc.shipping_address_name) {
			wn.model.with_doc("Address", this.frm.doc.shipping_address_name, function(name) {
				var address = wn.model.get_doc("Address", name);
			
				var out = $.map(["address_line1", "address_line2", "city"], 
					function(f) { return address[f]; });

				var state_pincode = $.map(["state", "pincode"], function(f) { return address[f]; }).join(" ");
				if(state_pincode) out.push(state_pincode);
			
				if(address["country"]) out.push(address["country"]);
			
				out.concat($.map([["Phone:", address["phone"]], ["Fax:", address["fax"]]], 
					function(val) { return val[1] ? val.join(" ") : null; }));
			
				me.frm.set_value("shipping_address", out.join("\n"));
			});
		}
	}
});

// Help for Sales BOM items
var set_sales_bom_help = function(doc) {
	if(!cur_frm.fields_dict.packing_list) return;
	if (getchildren('Packed Item', doc.name, 'packing_details').length) {
		$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(true);
		
		if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			help_msg = "<div class='alert alert-warning'>" +
				wn._("For 'Sales BOM' items, warehouse, serial no and batch no \
				will be considered from the 'Packing List' table. \
				If warehouse and batch no are same for all packing items for any 'Sales BOM' item, \
				those values can be entered in the main item table, values will be copied to 'Packing List' table.")+
			"</div>";
			wn.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = help_msg;
		} 
	} else {
		$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(false);
		if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			wn.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = '';
		}
	}
	refresh_field('sales_bom_help');
}
