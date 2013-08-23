// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext");
wn.require("app/js/controllers/stock_controller.js");

erpnext.TransactionController = erpnext.stock.StockController.extend({
	onload: function() {
		var me = this;
		if(this.frm.doc.__islocal) {
			var today = get_today(),
				currency = wn.defaults.get_default("currency");
			
			$.each({
				posting_date: today,
				due_date: today,
				transaction_date: today,
				currency: currency,
				price_list_currency: currency,
				status: "Draft",
				company: wn.defaults.get_default("company"),
				fiscal_year: wn.defaults.get_default("fiscal_year"),
				is_subcontracted: "No",
				conversion_rate: 1.0,
				plc_conversion_rate: 1.0
			}, function(fieldname, value) {
				if(me.frm.fields_dict[fieldname] && !me.frm.doc[fieldname])
					me.frm.set_value(fieldname, value);
			});
			
			me.frm.script_manager.trigger("company");
		}
		
		if(this.other_fname) {
			this[this.other_fname + "_remove"] = this.calculate_taxes_and_totals;
		}
		
		if(this.fname) {
			this[this.fname + "_remove"] = this.calculate_taxes_and_totals;
		}
	},
	
	onload_post_render: function() {
		if(this.frm.doc.__islocal && this.frm.doc.company && !this.frm.doc.customer) {
			var me = this;
			return this.frm.call({
				doc: this.frm.doc,
				method: "onload_post_render",
				freeze: true,
				callback: function(r) {
					// remove this call when using client side mapper
					me.set_default_values();
					me.set_dynamic_labels();
				}
			});
		}
	},
	
	refresh: function() {
		this.frm.clear_custom_buttons();
		erpnext.hide_naming_series();
		erpnext.hide_company();
		this.show_item_wise_taxes();
		this.set_dynamic_labels();
	},
	
	validate: function() {
		this.calculate_taxes_and_totals();
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
	
	company: function() {
		if(this.frm.doc.company && this.frm.fields_dict.currency) {
			if(!this.frm.doc.currency) {
				this.frm.set_value("currency", this.get_company_currency());
			}
			
			this.frm.script_manager.trigger("currency");
		}
	},
	
	get_company_currency: function() {
		return erpnext.get_currency(this.frm.doc.company);
	},
	
	currency: function() {
		var me = this;
		this.set_dynamic_labels();
		
		var company_currency = this.get_company_currency();
		if(this.frm.doc.currency !== company_currency) {
			this.get_exchange_rate(this.frm.doc.currency, company_currency, 
				function(exchange_rate) {
					if(exchange_rate) {
						me.frm.set_value("conversion_rate", exchange_rate);
						me.conversion_rate();
					}
				});
		} else {
			this.conversion_rate();		
		}
	},
	
	conversion_rate: function() {
		if(this.frm.doc.currency === this.get_company_currency()) {
			this.frm.set_value("conversion_rate", 1.0);
		} else if(this.frm.doc.currency === this.frm.doc.price_list_currency &&
			this.frm.doc.plc_conversion_rate !== this.frm.doc.conversion_rate) {
				this.frm.set_value("plc_conversion_rate", this.frm.doc.conversion_rate);
		}
		
		this.calculate_taxes_and_totals();
	},
	
	get_price_list_currency: function(buying_or_selling) {
		var me = this;
		var fieldname = buying_or_selling.toLowerCase() + "_price_list";
		if(this.frm.doc[fieldname]) {
			return this.frm.call({
				method: "setup.utils.get_price_list_currency",
				args: { 
					price_list: this.frm.doc[fieldname],
				},
				callback: function(r) {
					if(!r.exc) {
						me.price_list_currency();
					}
				}
			});
		}
	},
	
	get_exchange_rate: function(from_currency, to_currency, callback) {
		var exchange_name = from_currency + "-" + to_currency;
		wn.model.with_doc("Currency Exchange", exchange_name, function(name) {
			var exchange_doc = wn.model.get_doc("Currency Exchange", exchange_name);
			callback(exchange_doc ? flt(exchange_doc.exchange_rate) : 0);
		});
	},
	
	price_list_currency: function() {
		this.set_dynamic_labels();
		
		var company_currency = this.get_company_currency();
		if(this.frm.doc.price_list_currency !== company_currency) {
			this.get_exchange_rate(this.frm.doc.price_list_currency, company_currency, 
				function(exchange_rate) {
					if(exchange_rate) {
						me.frm.set_value("price_list_currency", exchange_rate);
						me.plc_conversion_rate();
					}
				});
		} else {
			this.plc_conversion_rate();
		}
	},
	
	plc_conversion_rate: function() {
		if(this.frm.doc.price_list_currency === this.get_company_currency()) {
			this.frm.set_value("plc_conversion_rate", 1.0);
		} else if(this.frm.doc.price_list_currency === this.frm.doc.currency) {
			this.frm.set_value("conversion_rate", this.frm.doc.plc_conversion_rate);
			this.calculate_taxes_and_totals();
		}
	},
	
	qty: function(doc, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},
	
	tax_rate: function(doc, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},
	
	row_id: function(doc, cdt, cdn) {
		var tax = wn.model.get_doc(cdt, cdn);
		try {
			this.validate_on_previous_row(tax);
			this.calculate_taxes_and_totals();
		} catch(e) {
			tax.row_id = null;
			refresh_field("row_id", tax.name, tax.parentfield);
			throw e;
		}
	},
	
	set_dynamic_labels: function() {
		// What TODO? should we make price list system non-mandatory?
		this.frm.toggle_reqd("plc_conversion_rate",
			!!(this.frm.doc.price_list_name && this.frm.doc.price_list_currency));
			
		var company_currency = this.get_company_currency();
		this.change_form_labels(company_currency);
		this.change_grid_labels(company_currency);
		this.frm.refresh_fields();
	},
	
	recalculate: function() {
		this.calculate_taxes_and_totals();
	},
	
	recalculate_values: function() {
		this.calculate_taxes_and_totals();
	},
	
	calculate_charges: function() {
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
	
	get_item_wise_taxes_html: function() {
		var item_tax = {};
		var tax_accounts = [];
		var company_currency = this.get_company_currency();
		
		$.each(this.get_tax_doclist(), function(i, tax) {
			var tax_amount_precision = precision("tax_amount", tax);
			var tax_rate_precision = precision("rate", tax);
			$.each(JSON.parse(tax.item_wise_tax_detail || '{}'), 
				function(item_code, tax_data) {
					if(!item_tax[item_code]) item_tax[item_code] = {};
					if($.isArray(tax_data)) {
						var tax_rate = "";
						if(tax_data[0] != null) {
							tax_rate = (tax.charge_type === "Actual") ?
								format_currency(flt(tax_data[0], tax_amount_precision), company_currency, tax_amount_precision) :
								(flt(tax_data[0], tax_rate_precision) + "%");
						}
						var tax_amount = format_currency(flt(tax_data[1], tax_amount_precision), company_currency,
							tax_amount_precision);
						
						item_tax[item_code][tax.name] = [tax_rate, tax_amount];
					} else {
						item_tax[item_code][tax.name] = [flt(tax_data, tax_rate_precision) + "%", ""];
					}
				});
			tax_accounts.push([tax.name, tax.account_head]);
		});
		
		var headings = $.map([wn._("Item Name")].concat($.map(tax_accounts, function(head) { return head[1]; })), 
			function(head) { return '<th style="min-width: 100px;">' + (head || "") + "</th>" }).join("\n");
		
		var rows = $.map(this.get_item_doclist(), function(item) {
			var item_tax_record = item_tax[item.item_code || item.item_name];
			if(!item_tax_record) { return null; }
			return repl("<tr><td>%(item_name)s</td>%(taxes)s</tr>", {
				item_name: item.item_name,
				taxes: $.map(tax_accounts, function(head) {
					return item_tax_record[head[0]] ?
						"<td>(" + item_tax_record[head[0]][0] + ") " + item_tax_record[head[0]][1] + "</td>" :
						"<td></td>";
				}).join("\n")
			});
		}).join("\n");
		
		if(!rows) return "";
		return '<div style="overflow-x: scroll;"><table class="table table-bordered table-hover">\
			<thead><tr>' + headings + '</tr></thead> \
			<tbody>' + rows + '</tbody> \
		</table></div>';
	},
	
	_validate_before_fetch: function(fieldname) {
		var me = this;
		if(!me.frm.doc[fieldname]) {
			return (wn._("Please specify") + ": " + 
				wn.meta.get_label(me.frm.doc.doctype, fieldname, me.frm.doc.name) + 
				". " + wn._("It is needed to fetch Item Details."));
		}
		return null;
	},
	
	validate_company_and_party: function(party_field) {
		var me = this;
		var valid = true;
		var msg = "";
		$.each(["company", party_field], function(i, fieldname) {
			var msg_for_fieldname = me._validate_before_fetch(fieldname);
			if(msg_for_fieldname) {
				msgprint(msg_for_fieldname);
				valid = false;
			}
		});
		return valid;
	},
	
	get_item_doclist: function() {
		return wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name,
			{parentfield: this.fname});
	},
	
	get_tax_doclist: function() {
		return wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name,
			{parentfield: this.other_fname});
	},
	
	validate_conversion_rate: function() {
		this.frm.doc.conversion_rate = flt(this.frm.doc.conversion_rate, precision("conversion_rate"));
		var conversion_rate_label = wn.meta.get_label(this.frm.doc.doctype, "conversion_rate", 
			this.frm.doc.name);
		
		if(this.frm.doc.conversion_rate == 0) {
			wn.throw(wn._(conversion_rate_label) + " " + wn._("cannot be 0"));
		}
		
		var company_currency = this.get_company_currency();
		var valid_conversion_rate = this.frm.doc.conversion_rate ?
			((this.frm.doc.currency == company_currency && this.frm.doc.conversion_rate == 1.0) ||
			(this.frm.doc.currency != company_currency && this.frm.doc.conversion_rate != 1.0)) :
			false;
		
		if(!valid_conversion_rate) {
			wn.throw(wn._("Please enter valid") + " " + wn._(conversion_rate_label) + 
				" 1 " + this.frm.doc.currency + " = [?] " + company_currency);
		}
	},
	
	calculate_taxes_and_totals: function() {
		this.validate_conversion_rate();
		this.frm.item_doclist = this.get_item_doclist();
		this.frm.tax_doclist = this.get_tax_doclist();
		
		this.calculate_item_values();
		this.initialize_taxes();
		this.determine_exclusive_rate && this.determine_exclusive_rate();
		this.calculate_net_total();
		this.calculate_taxes();
		this.calculate_totals();
		this._cleanup();
		
		this.show_item_wise_taxes();
	},
	
	initialize_taxes: function() {
		var me = this;
		$.each(this.frm.tax_doclist, function(i, tax) {
			tax.item_wise_tax_detail = {};
			$.each(["tax_amount", "total",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"],
				function(i, fieldname) { tax[fieldname] = 0.0 });
			
			me.validate_on_previous_row(tax);
			me.validate_inclusive_tax(tax);
			wn.model.round_floats_in(tax);
		});
	},
	
	calculate_taxes: function() {
		var me = this;
		
		$.each(this.frm.item_doclist, function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			
			$.each(me.frm.tax_doclist, function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);

				me.set_item_tax_amount && me.set_item_tax_amount(item, tax, current_tax_amount);
				
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
				
				// for buying
				if(tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = (tax.category == "Valuation") ? 0.0 : current_tax_amount;
					
					current_tax_amount *= (tax.add_deduct_tax == "Deduct") ? -1.0 : 1.0;
				}
				
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
		
		current_tax_amount = flt(current_tax_amount, precision("tax_amount", tax));
		
		// store tax breakup for each item
		tax.item_wise_tax_detail[item.item_code || item.item_name] = [tax_rate, current_tax_amount];
		
		return current_tax_amount;
	},
	
	_cleanup: function() {
		$.each(this.frm.tax_doclist, function(i, tax) {
			$.each(["tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"], 
				function(i, fieldname) { delete tax[fieldname]; });
			
			tax.item_wise_tax_detail = JSON.stringify(tax.item_wise_tax_detail);
		});
	},

	calculate_total_advance: function(parenttype, advance_parentfield) {
		if(this.frm.doc.doctype == parenttype && this.frm.doc.docstatus < 2) {
			var advance_doclist = wn.model.get_doclist(this.frm.doc.doctype, this.frm.doc.name, 
				{parentfield: advance_parentfield});
			this.frm.doc.total_advance = flt(wn.utils.sum(
				$.map(advance_doclist, function(adv) { return adv.allocated_amount })
			), precision("total_advance"));
			
			this.calculate_outstanding_amount();
		}
	},
	
	_set_in_company_currency: function(item, print_field, base_field) {
		// set values in base currency
		item[base_field] = flt(item[print_field] * this.frm.doc.conversion_rate,
			precision(base_field, item));
	},
	
	get_terms: function() {
		var me = this;
		if(this.frm.doc.tc_name) {
			return this.frm.call({
				method: "webnotes.client.get_value",
				args: {
					doctype: "Terms and Conditions",
					fieldname: "terms",
					filters: { name: this.frm.doc.tc_name },
				},
			});
		}
	},
});