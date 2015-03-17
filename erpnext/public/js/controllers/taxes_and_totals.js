// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
frappe.require("assets/erpnext/js/controllers/stock_controller.js");

erpnext.taxes_and_totals = erpnext.stock.StockController.extend({
	calculate_taxes_and_totals: function(update_paid_amount) {
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();

		if (frappe.meta.get_docfield(this.frm.doc.doctype, "discount_amount"))
			this.apply_discount_amount();

		// Advance calculation applicable to Sales /Purchase Invoice
		if(in_list(["Sales Invoice", "Purchase Invoice"], this.frm.doc.doctype) && this.frm.doc.docstatus < 2) {
			this.calculate_total_advance(update_paid_amount);
		}

		// Sales person's commission
		if(in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"], this.frm.doc.doctype)) {
			this.calculate_commission();
			this.calculate_contribution();
		}

		this.frm.refresh_fields();
	},

	_calculate_taxes_and_totals: function() {
		this.validate_conversion_rate();
		this.calculate_item_values();
		this.initialize_taxes();
		this.determine_exclusive_rate();
		this.calculate_net_total();
		this.calculate_taxes();
		this.manipulate_grand_total_for_inclusive_tax();
		this.calculate_totals();
		this._cleanup();
		this.show_item_wise_taxes();
	},

	validate_conversion_rate: function() {
		this.frm.doc.conversion_rate = flt(this.frm.doc.conversion_rate, precision("conversion_rate"));
		var conversion_rate_label = frappe.meta.get_label(this.frm.doc.doctype, "conversion_rate",
			this.frm.doc.name);
		var company_currency = this.get_company_currency();

		if(!this.frm.doc.conversion_rate) {
			frappe.throw(repl('%(conversion_rate_label)s' +
				__(' is mandatory. Maybe Currency Exchange record is not created for ') +
				'%(from_currency)s' + __(" to ") + '%(to_currency)s',
				{
					"conversion_rate_label": conversion_rate_label,
					"from_currency": this.frm.doc.currency,
					"to_currency": company_currency
				}));
		}
	},

	calculate_item_values: function() {
		var me = this;

		if (!this.discount_amount_applied) {
			$.each(this.frm.doc["items"] || [], function(i, item) {
				frappe.model.round_floats_in(item);
				item.net_rate = item.rate;
				item.amount = flt(item.rate * item.qty, precision("amount", item));
				item.net_amount = item.amount;
				item.item_tax_amount = 0.0;

				me.set_in_company_currency(item, ["price_list_rate", "rate", "amount", "net_rate", "net_amount"]);
			});
		}
	},

	set_in_company_currency: function(doc, fields) {
		var me = this;
		$.each(fields, function(i, f) {
			doc["base_"+f] = flt(flt(doc[f], precision(f, doc)) * me.frm.doc.conversion_rate, precision("base_" + f, doc));
		})
	},

	initialize_taxes: function() {
		var me = this;

		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			tax.item_wise_tax_detail = {};
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if (cstr(tax.charge_type) != "Actual" &&
				!(me.discount_amount_applied && me.frm.doc.apply_discount_on=="Grand Total"))
					tax_fields.push("tax_amount");

			$.each(tax_fields, function(i, fieldname) { tax[fieldname] = 0.0 });

			if (!this.discount_amount_applied) {
				cur_frm.cscript.validate_taxes_and_charges(tax.doctype, tax.name);
				me.validate_inclusive_tax(tax);
			}
			frappe.model.round_floats_in(tax);
		});
	},

	determine_exclusive_rate: function() {
		var me = this;

		var has_inclusive_tax = false;
		$.each(me.frm.doc["taxes"] || [], function(i, row) {
			if(cint(row.included_in_print_rate)) has_inclusive_tax = true;
		})
		if(has_inclusive_tax==false) return;

		$.each(me.frm.doc["items"] || [], function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			var cumulated_tax_fraction = 0.0;

			$.each(me.frm.doc["taxes"] || [], function(i, tax) {
				tax.tax_fraction_for_current_item = me.get_current_tax_fraction(tax, item_tax_map);

				if(i==0) {
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item;
				} else {
					tax.grand_total_fraction_for_current_item =
						me.frm.doc["taxes"][i-1].grand_total_fraction_for_current_item +
						tax.tax_fraction_for_current_item;
				}

				cumulated_tax_fraction += tax.tax_fraction_for_current_item;
			});

			if(cumulated_tax_fraction && !me.discount_amount_applied) {
				item.net_amount = flt(item.amount / (1 + cumulated_tax_fraction), precision("net_amount", item));
				item.net_rate = flt(item.net_amount / item.qty, precision("net_rate", item));

				me.set_in_company_currency(item, ["net_rate", "net_amount"]);

				// if(item.discount_percentage == 100) {
				// 	item.base_price_list_rate = item.base_rate;
				// 	item.base_rate = 0.0;
				// } else {
				// 	item.base_price_list_rate = flt(item.base_rate / (1 - item.discount_percentage / 100.0),
				// 		precision("base_price_list_rate", item));
				// }
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
					this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_fraction_for_current_item;

			} else if(tax.charge_type == "On Previous Row Total") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			}
		}

		return current_tax_fraction;
	},

	_get_tax_rate: function(tax, item_tax_map) {
		return (keys(item_tax_map).indexOf(tax.account_head) != -1) ?
			flt(item_tax_map[tax.account_head], precision("rate", tax)) : tax.rate;
	},

	calculate_net_total: function() {
		var me = this;
		this.frm.doc.total = this.frm.doc.base_total = this.frm.doc.net_total = this.frm.doc.base_net_total = 0.0;

		$.each(this.frm.doc["items"] || [], function(i, item) {
			me.frm.doc.total += item.amount;
			me.frm.doc.base_total += item.base_amount;
			me.frm.doc.net_total += item.net_amount;
			me.frm.doc.base_net_total += item.base_net_amount;
		});

		frappe.model.round_floats_in(this.frm.doc, ["total", "base_total", "net_total", "base_net_total"]);
	},

	calculate_taxes: function() {
		var me = this;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(this.frm.doc["items"] || [], function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);

			$.each(me.frm.doc["taxes"] || [], function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);

				// Adjust divisional loss to the last item
				if (tax.charge_type == "Actual") {
					actual_tax_dict[tax.idx] -= current_tax_amount;
					if (n == me.frm.doc["items"].length - 1) {
						current_tax_amount += actual_tax_dict[tax.idx]
					}
				}

				// accumulate tax amount into tax.tax_amount
				if (tax.charge_type != "Actual" &&
					!(me.discount_amount_applied && me.frm.doc.apply_discount_on=="Grand Total"))
						tax.tax_amount += current_tax_amount;

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// tax amount after discount amount
				tax.tax_amount_after_discount_amount += current_tax_amount;

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
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount, precision("total", tax));
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.doc["taxes"][i-1].grand_total_for_current_item + current_tax_amount, precision("total", tax));
				}

				// in tax.total, accumulate grand total for each item
				tax.total += tax.grand_total_for_current_item;

				// set precision in the last item iteration
				if (n == me.frm.doc["items"].length - 1) {
					me.round_off_totals(tax);

					// adjust Discount Amount loss in last tax iteration
					if ((i == me.frm.doc["taxes"].length - 1) && me.discount_amount_applied && me.frm.doc.apply_discount_on == "Grand Total")
						me.adjust_discount_amount_loss(tax);
				}
			});
		});
	},

	_load_item_tax_rate: function(item_tax_rate) {
		return item_tax_rate ? JSON.parse(item_tax_rate) : {};
	},

	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.net_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.net_amount;

		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		current_tax_amount = flt(current_tax_amount, precision("tax_amount", tax));

		this.set_item_wise_tax(item, tax, tax_rate, current_tax_amount);

		return current_tax_amount;
	},

	set_item_wise_tax: function(item, tax, tax_rate, current_tax_amount) {
		// store tax breakup for each item
		var key = item.item_code || item.item_name;
		var item_wise_tax_amount = current_tax_amount * this.frm.doc.conversion_rate;
		if (tax.item_wise_tax_detail && tax.item_wise_tax_detail[key])
			item_wise_tax_amount += tax.item_wise_tax_detail[key][1]

		tax.item_wise_tax_detail[key] = [tax_rate,flt(item_wise_tax_amount, precision("base_tax_amount", tax))]

	},

	round_off_totals: function(tax) {
		tax.total = flt(tax.total, precision("total", tax));
		tax.tax_amount = flt(tax.tax_amount, precision("tax_amount", tax));
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount, precision("tax_amount", tax));

		this.set_in_company_currency(tax, ["total", "tax_amount", "tax_amount_after_discount_amount"]);
	},

	adjust_discount_amount_loss: function(tax) {
		var discount_amount_loss = this.frm.doc.grand_total - flt(this.frm.doc.discount_amount) - tax.total;
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, precision("tax_amount", tax));
		tax.total = flt(tax.total + discount_amount_loss, precision("total", tax));
	},
	
	manipulate_grand_total_for_inclusive_tax: function() {
		var me = this;
		// if fully inclusive taxes and diff
		if (this.frm.doc["taxes"].length) {
			var all_inclusive = frappe.utils.all(this.frm.doc["taxes"].map(function(d) {
				return cint(d.included_in_print_rate);
			}));

			if (all_inclusive) {
				var last_tax = me.frm.doc["taxes"].slice(-1)[0];

				var diff = me.frm.doc.net_total
					- flt(last_tax.total / me.frm.doc.conversion_rate, precision("grand_total"));

				if ( diff && Math.abs(diff) <= (2.0 / Math.pow(10, last_tax.precision("tax_amount"))) ) {
					var adjustment_amount = flt(diff * me.frm.doc.conversion_rate, 
							last_tax.precision("tax_amount"));
					last_tax.tax_amount += adjustment_amount;
					last_tax.tax_amount_after_discount += adjustment_amount;
					last_tax.total += adjustment_amount;
				}
			}
		}
	},

	calculate_totals: function() {
		// Changing sequence can cause roundiing issue and on-screen discrepency
		var me = this;
		var tax_count = this.frm.doc["taxes"] ? this.frm.doc["taxes"].length : 0;
		this.frm.doc.grand_total = flt(tax_count ? this.frm.doc["taxes"][tax_count - 1].total : this.frm.doc.net_total);

		if(in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"], this.frm.doc.doctype)) {
			this.frm.doc.base_grand_total = (this.frm.doc.total_taxes_and_charges) ?
				flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate) : this.frm.doc.base_net_total;
		} else {
			// other charges added/deducted
			this.frm.doc.taxes_and_charges_added = this.frm.doc.taxes_and_charges_deducted = 0.0;
			if(tax_count) {
				$.each(this.frm.doc["taxes"] || [], function(i, tax) {
					if (in_list(["Valuation and Total", "Total"], tax.category)) {
						if(tax.add_deduct_tax == "Add") {
							me.frm.doc.taxes_and_charges_added += flt(tax.tax_amount);
						} else {
							me.frm.doc.taxes_and_charges_deducted += flt(tax.tax_amount);
						}
					}
				})

				frappe.model.round_floats_in(this.frm.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"]);
			}

			this.frm.doc.base_grand_total = flt((this.frm.doc.taxes_and_charges_added || this.frm.doc.taxes_and_charges_deducted) ?
				flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate) : this.frm.doc.base_net_total);

			this.set_in_company_currency(this.frm.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"]);
		}

		this.frm.doc.total_taxes_and_charges = flt(this.frm.doc.grand_total - this.frm.doc.net_total,
			precision("total_taxes_and_charges"));

		this.set_in_company_currency(this.frm.doc, ["total_taxes_and_charges"]);

		// Round grand total as per precision
		frappe.model.round_floats_in(this.frm.doc, ["grand_total", "base_grand_total"]);

		// rounded totals
		if(frappe.meta.get_docfield(this.frm.doc.doctype, "rounded_total", this.frm.doc.name)) {
			this.frm.doc.rounded_total = Math.round(this.frm.doc.grand_total);
		}
		if(frappe.meta.get_docfield(this.frm.doc.doctype, "base_rounded_total", this.frm.doc.name)) {
			this.frm.doc.base_rounded_total = Math.round(this.frm.doc.base_grand_total);
		}
	},

	_cleanup: function() {
		this.frm.doc.base_in_words = this.frm.doc.in_words = "";

		if(this.frm.doc["items"] && this.frm.doc["items"].length) {
			if(!frappe.meta.get_docfield(this.frm.doc["items"][0].doctype, "item_tax_amount", this.frm.doctype)) {
				$.each(this.frm.doc["items"] || [], function(i, item) {
					delete item["item_tax_amount"];
				});
			}
		}

		if(this.frm.doc["taxes"] && this.frm.doc["taxes"].length) {
			var temporary_fields = ["tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if(!frappe.meta.get_docfield(this.frm.doc["taxes"][0].doctype, "tax_amount_after_discount_amount", this.frm.doctype)) {
				temporary_fields.push("tax_amount_after_discount_amount");
			}

			$.each(this.frm.doc["taxes"] || [], function(i, tax) {
				$.each(temporary_fields, function(i, fieldname) {
					delete tax[fieldname];
				});

				tax.item_wise_tax_detail = JSON.stringify(tax.item_wise_tax_detail);
			});
		}
	},

	apply_discount_amount: function() {
		var me = this;
		var distributed_amount = 0.0;

		if (this.frm.doc.discount_amount) {
			if(!this.frm.doc.apply_discount_on)
				frappe.throw(__("Please select Apply Discount On"));

			this.frm.set_value("base_discount_amount",
				flt(this.frm.doc.discount_amount * this.frm.doc.conversion_rate, precision("base_discount_amount")))

			var total_for_discount_amount = this.get_total_for_discount_amount();
			// calculate item amount after Discount Amount
			if (total_for_discount_amount) {
				$.each(this.frm.doc["items"] || [], function(i, item) {
					distributed_amount = flt(me.frm.doc.discount_amount) * item.net_amount / total_for_discount_amount;
					item.net_amount = flt(item.net_amount - distributed_amount, precision("base_amount", item));
					item.net_rate = flt(item.net_amount / item.qty, precision("net_rate", item));

					me.set_in_company_currency(item, ["net_rate", "net_amount"]);
				});

				this.discount_amount_applied = true;
				this._calculate_taxes_and_totals();
			}
		} else {
			this.frm.set_value("base_discount_amount", 0);
		}
	},

	get_total_for_discount_amount: function() {
		var me = this;

		if(this.frm.doc.apply_discount_on == "Net Total") {
			return this.frm.doc.net_total
		} else {
			var total_actual_tax = 0.0;
			var actual_taxes_dict = {};

			$.each(this.frm.doc["taxes"] || [], function(i, tax) {
				if (tax.charge_type == "Actual")
					actual_taxes_dict[tax.idx] = tax.tax_amount;
				else if (actual_taxes_dict[tax.row_id] !== null) {
					actual_tax_amount = flt(actual_taxes_dict[tax.row_id]) * flt(tax.rate) / 100;
					actual_taxes_dict[tax.idx] = actual_tax_amount;
				}
			});

			$.each(actual_taxes_dict, function(key, value) {
				if (value) total_actual_tax += value;
			});

			return flt(this.frm.doc.grand_total - total_actual_tax, precision("grand_total"));
		}
	},

	calculate_total_advance: function(update_paid_amount) {
		var total_allocated_amount = frappe.utils.sum($.map(this.frm.doc["advances"] || [], function(adv) {
			return flt(adv.allocated_amount, precision("allocated_amount", adv))
		}));
		this.frm.doc.total_advance = flt(total_allocated_amount, precision("total_advance"));

		this.calculate_outstanding_amount(update_paid_amount);
	}
})
