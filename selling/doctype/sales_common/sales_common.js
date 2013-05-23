// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname
// cur_frm.cscript.other_fname - wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js'); fieldname
// cur_frm.cscript.sales_team_fname - Sales Team fieldname

wn.provide("erpnext.selling");

erpnext.selling.SellingController = wn.ui.form.Controller.extend({
	setup: function() {
		this.frm.add_fetch("sales_partner", "commission_rate", "commission_rate");
	},
	
	// events when rendering form
	// 1
	onload: function() {
		var me = this;
		this.toggle_rounded_total();
		if(this.frm.doc.__islocal) {
			// set date fields
			$.each(["posting_date", "due_date", "transaction_date"], function(i, fieldname) {
				if(me.frm.fields_dict[fieldname] && !me.frm.doc[fieldname]) {
					me.frm.set_value(fieldname, get_today());
				}
			});
			
			// set currency fields
			$.each(["currency", "price_list_currency"], function(i, fieldname) {
				if(me.frm.fields_dict[fieldname] && !me.frm.doc[fieldname]) {
					me.frm.set_value(fieldname, wn.defaults.get_default("currency"));
				}
			});
			
			// status
			if(!this.frm.doc.status) this.frm.set_value("status", "Draft");
			
			// TODO set depends_on for customer related fields
		}
	},
	
	// 2
	refresh: function() {
		erpnext.hide_naming_series();
		this.show_item_wise_taxes();
		this.set_dynamic_labels();
	},
	
	// 3
	onload_post_render: function() {
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			var me = this;
			this.frm.call({
				doc: this.frm.doc,
				method: "onload_post_render",
				freeze: true,
				callback: function(r) {
					// remove this call when using client side mapper
					me.set_default_values();
					me.frm.refresh();
				}
			});
		}
	},
	
	validate: function() {
		this.calculate_taxes_and_totals();
		
		// TODO calc adjustment amount
	},
	
	barcode: function(doc, cdt, cdn) {
		this.item_code(doc, cdt, cdn);
	},
	
	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code || item.barcode) {
			if(!this.validate_company_and_party()) {
				item.item_code = null;
				refresh_field("item_code", item.name, item.parentfield);
			} else {
				this.frm.call({
					method: "selling.utils.get_item_details",
					child: item,
					args: {
						args: {
							item_code: item.item_code,
							barcode: item.barcode,
							warehouse: item.warehouse,
							doctype: me.frm.doc.doctype,
							customer: me.frm.doc.customer,
							currency: me.frm.doc.currency,
							conversion_rate: me.frm.doc.conversion_rate,
							price_list_name: me.frm.doc.price_list_name,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							company: me.frm.doc.company,
							order_type: me.frm.doc.order_type,
							is_pos: cint(me.frm.doc.is_pos),
							update_stock: cint(me.frm.doc.update_stock),
						}
					},
					callback: function(r) {
						if(!r.exc) {
							me.ref_rate(me.frm.doc, cdt, cdn);
						}
					}
				});
			}
		}
	},
	
	company: function() {
		if(this.frm.doc.company) {
			var me = this;
			var company_currency = this.get_company_currency();
			$.each(["currency", "price_list_currency"], function(i, fieldname) {
				if(!me.doc[fieldname]) {
					me.frm.set_value(fieldname, company_currency);
				}
			});
			this.price_list_currency();
		}
	},
	
	customer: function() {
		if(this.frm.doc.customer || this.frm.doc.debit_to) {
			if(!this.frm.doc.company) {
				this.frm.set_value("customer", null);
				msgprint(wn._("Please specify Company"));
			} else {
				var me = this;
				var price_list_name = this.frm.doc.price_list_name;

				this.frm.call({
					doc: this.frm.doc,
					method: "set_customer_defaults",
					freeze: true,
					callback: function(r) {
						if(!r.exc) {
							me.frm.refresh_fields();
							if(me.frm.doc.price_list_name !== price_list_name) me.price_list_name();
						}
					}
				});
			}
		}
		
		// TODO hide/unhide related fields
	},
	
	price_list_name: function() {
		var me = this;
		if(this.frm.doc.price_list_name) {
			this.frm.call({
				method: "setup.utils.get_price_list_currency",
				args: {args: {
					price_list_name: this.frm.doc.price_list_name,
					use_for: "selling"
				}},
				callback: function(r) {
					if(!r.exc) {
						me.price_list_currency();
					}
				}
			});
		}
	},
	
	currency: function() {
		this.price_list_currency();
	},
	
	price_list_currency: function() {
		// What TODO? should we make price list system non-mandatory?
		// this.frm.toggle_reqd("plc_conversion_rate",
		// 	!!(this.frm.doc.price_list_name && this.frm.doc.price_list_currency));
		
		if(this.frm.doc.price_list_currency === this.get_company_currency()) {
			this.frm.set_value("plc_conversion_rate", 1.0);
			this.calculate_taxes_and_totals();
		} else if(this.frm.doc.price_list_currency === this.frm.doc.currency) {
			this.frm.set_value("plc_conversion_rate", this.frm.doc.conversion_rate);
			this.calculate_taxes_and_totals();
		}
		
		this.set_dynamic_labels();
	},
	
	conversion_rate: function() {
		this.price_list_currency();
		this.calculate_taxes_and_totals();
	},
	
	plc_conversion_rate: function() {
		this.price_list_currency();
	},
	
	ref_rate: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		wn.model.round_floats_in(item, ["ref_rate", "adj_rate"]);
		
		item.export_rate = flt(item.ref_rate * (1 - item.adj_rate / 100.0),
			precision("export_rate", item));
		
		this.calculate_taxes_and_totals();
	},
	
	qty: function(doc, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},
	
	adj_rate: function(doc, cdt, cdn) {
		this.ref_rate(doc, cdt, cdn);
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
	
	included_in_print_rate: function(doc, cdt, cdn) {
		var tax = wn.model.get_doc(cdt, cdn);
		try {
			this.validate_on_previous_row(tax);
			this.validate_inclusive_tax(tax);
			this.calculate_taxes_and_totals();
		} catch(e) {
			tax.included_in_print_rate = 0;
			refresh_field("included_in_print_rate", tax.name, tax.parentfield);
			throw e;
		}
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
	
	toggle_rounded_total: function() {
		var me = this;
		if(cint(wn.defaults.get_global_default("disable_rounded_total"))) {
			$.each(["rounded_total", "rounded_total_export"], function(i, fieldname) {
				me.frm.set_df_property(fieldname, "print_hide", 1);
				me.frm.toggle_display(fieldname, false);
			});
		}
	},
	
	validate_company_and_party: function() {
		var me = this;
		var valid = true;
		$.each(["company", "customer"], function(i, fieldname) {
			if(!me.frm.doc[fieldname]) {
				valid = false;
				msgprint(wn._("Please specify") + ": " + 
					wn.meta.get_label(me.frm.doc.doctype, fieldname, me.frm.doc.name) + 
					". " + wn._("It is needed to fetch Item Details."));
			}
		});
		return valid;
	},
	
	set_default_values: function() {
		$.each(wn.model.get_doclist(this.frm.doctype, this.frm.docname), function(i, doc) {
			var updated = wn.model.set_default_values(doc);
			if(doc.parentfield) {
				refresh_field(doc.parentfield);
			} else {
				refresh_field(updated);
			}
		});
	},
	
	calculate_taxes_and_totals: function() {
		this.frm.doc.conversion_rate = flt(this.frm.doc.conversion_rate, precision("conversion_rate"));
		
		// TODO validate conversion rate
		
		this.frm.item_doclist = this.get_item_doclist();
		this.frm.tax_doclist = this.get_tax_doclist();
		
		this.calculate_item_values();
		this.initialize_taxes();
		this.determine_exclusive_rate();
		this.calculate_net_total();
		this.calculate_taxes();
		this.calculate_totals();
		this.calculate_commission();
		this.calculate_contribution();
		this._cleanup();
		this.frm.doc.in_words = this.frm.doc.in_words_export = "";
		
		// TODO
		// outstanding amount
		
		// check for custom_recalc in custom scripts of server
		
		this.frm.refresh_fields();
		this.show_item_wise_taxes();
				
	},
	
	get_item_doclist: function() {
		return wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name,
			{parentfield: this.fname});
	},
	
	get_tax_doclist: function() {
		return wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name,
			{parentfield: "other_charges"});
	},
	
	calculate_item_values: function() {
		var me = this;
		
		var _set_base = function(item, print_field, base_field) {
			// set values in base currency
			item[base_field] = flt(item[print_field] * me.frm.doc.conversion_rate,
				precision(base_field, item));
		};
		
		$.each(this.frm.item_doclist, function(i, item) {
			wn.model.round_floats_in(item);
			item.export_amount = flt(item.export_rate * item.qty, precision("export_amount", item));
			
			_set_base(item, "ref_rate", "base_ref_rate");
			_set_base(item, "export_rate", "basic_rate");
			_set_base(item, "export_amount", "amount");
		});
		
	},
	
	initialize_taxes: function() {
		var me = this;
		$.each(this.frm.tax_doclist, function(i, tax) {
			tax.tax_amount = tax.total = 0.0;
			tax.item_wise_tax_detail = {};
			
			// temporary fields
			tax.tax_amount_for_current_item = tax.grand_total_for_current_item = 0.0;
			tax.tax_fraction_for_current_item = tax.grand_total_fraction_for_current_item = 0.0;
			
			me.validate_on_previous_row(tax);
			me.validate_inclusive_tax(tax);
			
			wn.model.round_floats_in(tax);
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
				item.basic_rate = flt(
					(item.export_rate * me.frm.doc.conversion_rate) / (1 + cumulated_tax_fraction),
					precision("basic_rate", item));
				
				item.amount = flt(item.basic_rate * item.qty, precision("amount", item));
				
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
	
	calculate_taxes: function() {
		var me = this;
		
		$.each(this.frm.item_doclist, function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			
			$.each(me.frm.tax_doclist, function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);
				
				// case when net total is 0 but there is an actual type charge
				// in this case add the actual amount to tax.tax_amount
				// and tax.grand_total_for_current_item for the first such iteration
				if(tax.charge_type == "Actual" && 
					!(current_tax_amount || me.frm.doc.net_total || tax.tax_amount)) {
						var zero_net_total_adjustment = flt(tax.rate, precision("tax_amount", tax));
						current_tax_amount += zero_net_total_adjustment;
					}
				
				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;
				
				// accumulate tax amount into tax.tax_amount
				tax.tax_amount += current_tax_amount;
				
				// Calculate tax.total viz. grand total till that step
				// note: grand_total_for_current_item contains the contribution of 
				// item's amount, previously applied tax and the current tax on that item
				if(i==0) {
					tax.grand_total_for_current_item = flt(item.amount + current_tax_amount,
						precision("total", tax));
				} else {
					tax.grand_total_for_current_item = 
						flt(me.frm.tax_doclist[i-1].grand_total_for_current_item + current_tax_amount,
							precision("total", tax));
				}
				
				// in tax.total, accumulate grand total for each item
				tax.total += tax.grand_total_for_current_item;
				
				// store tax breakup for each item
				tax.item_wise_tax_detail[item.item_code || item.item_name] = current_tax_amount;
				
			});
		});
	},
	
	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;
		
		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.rate, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.amount / this.frm.doc.net_total) * actual) :
				0.0;
			
		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.amount;
			
		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.tax_doclist[cint(tax.row_id) - 1].tax_amount_for_current_item;
			
		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.tax_doclist[cint(tax.row_id) - 1].grand_total_for_current_item;
			
		}
		
		return flt(current_tax_amount, precision("tax_amount", tax));
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
	
	calculate_commission: function() {
		if(this.frm.doc.commission_rate > 100) {
			var msg = wn._(wn.meta.get_label(this.frm.doc.doctype, "commission_rate", this.frm.doc.name)) +
				" " + wn._("cannot be greater than 100");
			msgprint(msg);
			throw msg;
		}
		
		this.frm.doc.total_commission = flt(this.frm.doc.net_total * this.frm.doc.commission_rate / 100.0,
			precision("total_commission"));
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
		$.each(this.frm.tax_doclist, function(i, tax) {
			var tax_fields = keys(tax);
			$.each(["tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"], 
				function(i, fieldname) { delete tax[fieldname];});
			
			tax.item_wise_tax_detail = JSON.stringify(tax.item_wise_tax_detail);
		});
	},
	
	validate_on_previous_row: function(tax) {
		// validate if a valid row id is mentioned in case of
		// On Previous Row Amount and On Previous Row Total
		if((["On Previous Row Amount", "On Previous Row Total"].indexOf(tax.charge_type) != -1) &&
			(!tax.row_id || cint(tax.row_id) >= tax.idx)) {
				var msg = repl(wn._("Row") + " # %(idx)s [%(doctype)s]: " +
					wn._("Please specify a valid") + " %(row_id_label)s", {
						idx: tax.idx,
						doctype: tax.doctype,
						row_id_label: wn.meta.get_label(tax.doctype, "row_id", tax.name)
					});
				msgprint(msg);
				throw msg;
			}
	},
	
	validate_inclusive_tax: function(tax) {
		if(!this.frm.tax_doclist) this.frm.tax_doclist = this.get_tax_doclist();
		
		var actual_type_error = function() {
			var msg = repl(wn._("For row") + " # %(idx)s [%(doctype)s]: " + 
				"%(charge_type_label)s = \"%(charge_type)s\" " +
				wn._("cannot be included in Item's rate"), {
					idx: tax.idx,
					doctype: tax.doctype,
					charge_type_label: wn.meta.get_label(tax.doctype, "charge_type", tax.name),
					charge_type: tax.charge_type
				});
			msgprint(msg);
			throw msg;
		};
		
		var on_previous_row_error = function(row_range) {
			var msg = repl(wn._("For row") + " # %(idx)s [%(doctype)s]: " + 
				wn._("to be included in Item's rate, it is required that: ") + 
				" [" + wn._("Row") + " # %(row_range)s] " + wn._("also be included in Item's rate"), {
					idx: tax.idx,
					doctype: tax.doctype,
					charge_type_label: wn.meta.get_label(tax.doctype, "charge_type", tax.name),
					charge_type: tax.charge_type,
					inclusive_label: wn.meta.get_label(tax.doctype, "included_in_print_rate", tax.name),
					row_range: row_range,
				});
			
			msgprint(msg);
			throw msg;
		};
		
		if(cint(tax.included_in_print_rate)) {
			if(tax.charge_type == "Actual") {
				// inclusive tax cannot be of type Actual
				actual_type_error();
			} else if(tax.charge_type == "On Previous Row Amount" &&
				!cint(this.frm.tax_doclist[tax.row_id - 1].included_in_print_rate)) {
					// referred row should also be an inclusive tax
					on_previous_row_error(tax.row_id);
			} else if(tax.charge_type == "On Previous Row Total") {
				var taxes_not_included = $.map(this.frm.tax_doclist.slice(0, tax.row_id), 
					function(t) { return cint(t.included_in_print_rate) ? null : t; });
				if(taxes_not_included.length > 0) {
					// all rows above this tax should be inclusive
					on_previous_row_error(tax.row_id == 1 ? "1" : "1 - " + tax.row_id);
				}
			}
		}
	},
	
	_load_item_tax_rate: function(item_tax_rate) {
		return item_tax_rate ? JSON.parse(item_tax_rate) : {};
	},
	
	_get_tax_rate: function(tax, item_tax_map) {
		return (keys(item_tax_map).indexOf(tax.account_head) != -1) ?
			flt(item_tax_map[tax.account_head], precision("rate", tax)) :
			tax.rate;
	},

	show_item_wise_taxes: function() {
		$(this.get_item_wise_taxes_html())
			.appendTo($(this.frm.fields_dict.other_charges_calculation.wrapper).empty());
	},
	
	get_item_wise_taxes_html: function() {
		var item_tax = {};
		var tax_accounts = [];
		var company_currency = this.get_company_currency();
		
		$.each(this.get_tax_doclist(), function(i, tax) {
			var tax_amount_precision = precision("tax_amount", tax);
			$.each(JSON.parse(tax.item_wise_tax_detail || '{}'), 
				function(item_code, tax_amount) {
					if(!item_tax[item_code]) item_tax[item_code] = {};
					item_tax[item_code][tax.account_head] = flt(tax_amount, tax_amount_precision);
				});
			tax_accounts.push(tax.account_head);
		});
		
		var headings = $.map([wn._("Item Name")].concat(tax_accounts), 
			function(head) { return '<th style="min-width: 100px;">' + (head || "") + "</th>" }).join("\n");
		
		var rows = $.map(this.get_item_doclist(), function(item) {
			var item_tax_record = item_tax[item.item_code || item.item_name];
			return repl("<tr><td>%(item_name)s</td>%(taxes)s</tr>", {
				item_name: item.item_name,
				taxes: $.map(tax_accounts, function(head) {
					return "<td>" + format_currency(item_tax_record[head], company_currency) + "</td>"
				}).join("\n")
			});
		}).join("\n");
		
		return '<div style="overflow-x: scroll;"><table class="table table-bordered table-hover">\
			<thead><tr>' + headings + '</tr></thead> \
			<tbody>' + rows + '</tbody> \
		</table></div>';
	},
	
	get_charges: function() {
		var me = this;
		if(this.frm.doc.charge) {
			this.frm.call({
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
	
	set_dynamic_labels: function() {
		var company_currency = this.get_company_currency();
		
		this.change_form_labels(company_currency);
		this.change_grid_labels(company_currency);
	},
	
	change_form_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};
		
		var setup_field_label_map = function(fields_list, currency) {
			$.each(fields_list, function(i, fname) {
				var docfield = wn.meta.get_docfield(me.frm.doc.doctype, fname);
				if(docfield) {
					var label = wn._((docfield.label || "")).replace(/\([^\)]*\)/g, "");
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
		
		setup_field_label_map(["conversion_rate"], 	"1 " + this.frm.doc.currency 
			+ " = [?] " + company_currency);
		
		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			setup_field_label_map(["plc_conversion_rate"], 	"1 " + this.frm.doc.price_list_currency 
				+ " = [?] " + company_currency);
		}
		
		// toggle fields
		this.frm.toggle_display(["conversion_rate", "net_total", "other_charges_total", 
			"grand_total", "rounded_total", "in_words"],
			this.frm.doc.currency != company_currency);
			
		this.frm.toggle_display(["plc_conversion_rate"], 
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
				var docfield = wn.meta.get_docfield(grid_doctype, fname);
				if(docfield) {
					var label = wn._((docfield.label || "")).replace(/\([^\)]*\)/g, "");
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
		var show = this.frm.doc.currency != company_currency;
		$.each(["basic_rate", "base_ref_rate", "amount"], function(i, fname) {
			if(wn.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, show);
		});
		
		// set labels
		var $wrapper = $(this.frm.wrapper);
		$.each(field_label_map, function(fname, label) {
			$wrapper.find('[data-grid-fieldname="'+fname+'"]').text(label);
		});
	},
	
	get_company_currency: function() {
		return erpnext.get_currency(this.frm.doc.company);
	}
});

// to save previous state of cur_frm.cscript
var prev_cscript = {};
$.extend(prev_cscript, cur_frm.cscript);

cur_frm.cscript = new erpnext.selling.SellingController({frm: cur_frm});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, prev_cscript);

// Help for Sales BOM items
var set_sales_bom_help = function(doc) {
	if(!cur_frm.fields_dict.packing_list) return;
	if (getchildren('Delivery Note Packing Item', doc.name, 'packing_details').length) {
		$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(true);
		
		if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			help_msg = "<div class='alert'> \
				For 'Sales BOM' items, warehouse, serial no and batch no \
				will be considered from the 'Packing List' table. \
				If warehouse and batch no are same for all packing items for any 'Sales BOM' item, \
				those values can be entered in the main item table, values will be copied to 'Packing List' table. \
			</div>";
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

cur_frm.fields_dict[cur_frm.cscript.fname].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	if (doc.order_type == "Maintenance") {
	 	return erpnext.queries.item({
			'ifnull(tabItem.is_service_item, "No")': 'Yes'
		});
	} else {
		return erpnext.queries.item({
			'ifnull(tabItem.is_sales_item, "No")': 'Yes'
		});
	}
}

cur_frm.fields_dict[cur_frm.cscript.fname].grid.get_field('batch_no').get_query = 
	function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code) {
			if (d.warehouse) {
				return "select batch_no from `tabStock Ledger Entry` sle \
					where item_code = '" + d.item_code + "' and warehouse = '" + d.warehouse +
					"' and ifnull(is_cancelled, 'No') = 'No' and batch_no like '%s' \
					and exists(select * from `tabBatch` where \
					name = sle.batch_no and expiry_date >= '" + doc.posting_date + 
					"' and docstatus != 2) group by batch_no having sum(actual_qty) > 0 \
					order by batch_no desc limit 50";
			} else {
				return "SELECT name FROM tabBatch WHERE docstatus != 2 AND item = '" + 
					d.item_code + "' and expiry_date >= '" + doc.posting_date + 
					"' AND name like '%s' ORDER BY name DESC LIMIT 50";
			}		
		} else {
			msgprint("Please enter Item Code to get batch no");
		}
	}

cur_frm.fields_dict.customer_address.on_new = function(dn) {
	locals['Address'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
	locals['Address'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
	locals['Contact'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
	locals['Contact'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name, address_line1, city FROM tabAddress \
		WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND \
		%(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name, CONCAT(first_name," ",ifnull(last_name,"")) As FullName, \
		department, designation FROM tabContact WHERE customer = "'+ doc.customer + 
		'" AND docstatus != 2 AND %(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
}

// ************* GET OTHER CHARGES BASED ON COMPANY *************
cur_frm.fields_dict.charge.get_query = function(doc) {
	return 'SELECT DISTINCT `tabSales Taxes and Charges Master`.name FROM \
		`tabSales Taxes and Charges Master` WHERE `tabSales Taxes and Charges Master`.company = "'
		+doc.company+'" AND `tabSales Taxes and Charges Master`.company is not NULL \
		AND `tabSales Taxes and Charges Master`.docstatus != 2 \
		AND `tabSales Taxes and Charges Master`.%(key)s LIKE "%s" \
		ORDER BY `tabSales Taxes and Charges Master`.name LIMIT 50';
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;