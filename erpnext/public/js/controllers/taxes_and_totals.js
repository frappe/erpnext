// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
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
		if(in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"])) {
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
		this.calculate_totals();
		this._cleanup();
		this.show_item_wise_taxes();
	},

	initialize_taxes: function() {
		var me = this;

		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			tax.item_wise_tax_detail = {};
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if (!me.discount_amount_applied)
				tax_fields.push("tax_amount");

			$.each(tax_fields, function(i, fieldname) { tax[fieldname] = 0.0 });

			me.validate_on_previous_row(tax);
			me.validate_inclusive_tax(tax);
			frappe.model.round_floats_in(tax);
		});
	},

	calculate_taxes: function() {
		var me = this;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.rate, precision("tax_amount", tax));
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

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// accumulate tax amount into tax.tax_amount
				if (!me.discount_amount_applied)
					tax.tax_amount += current_tax_amount;

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
					tax.grand_total_for_current_item = flt(item.base_amount + current_tax_amount,
						precision("total", tax));
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.doc["taxes"][i-1].grand_total_for_current_item + current_tax_amount,
							precision("total", tax));
				}

				// in tax.total, accumulate grand total for each item
				tax.total += tax.grand_total_for_current_item;

				// set precision in the last item iteration
				if (n == me.frm.doc["items"].length - 1) {
					me.round_off_totals(tax);

					// adjust Discount Amount loss in last tax iteration
					if ((i == me.frm.doc["taxes"].length - 1) && me.discount_amount_applied)
						me.adjust_discount_amount_loss(tax);
				}
			});
		});
	},

	round_off_totals: function(tax) {
		tax.total = flt(tax.total, precision("total", tax));
		tax.tax_amount = flt(tax.tax_amount, precision("tax_amount", tax));
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount,
			precision("tax_amount", tax));
	},

	adjust_discount_amount_loss: function(tax) {
		var discount_amount_loss = this.frm.doc.grand_total - flt(this.frm.doc.base_discount_amount) - tax.total;
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, precision("tax_amount", tax));
		tax.total = flt(tax.total + discount_amount_loss, precision("total", tax));
	},

	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.rate, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
			((item.base_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.base_amount;

		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		current_tax_amount = flt(current_tax_amount, precision("tax_amount", tax));

		// store tax breakup for each item
		tax.item_wise_tax_detail[item.item_code || item.item_name] = [tax_rate, current_tax_amount];

		return current_tax_amount;
	},

	_cleanup: function() {
		this.frm.doc.in_words = this.frm.doc.in_words_import = this.frm.doc.in_words_export = "";

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


	calculate_total_advance: function(update_paid_amount) {
		this.frm.doc.total_advance = flt(frappe.utils.sum(
			$.map(this.frm.doc["advances"] || [], function(adv) { return adv.allocated_amount })
		), precision("total_advance"));

		this.calculate_outstanding_amount(update_paid_amount);
	},

	calculate_item_values: function() {
		var me = this;

		if (!this.discount_amount_applied) {
			$.each(this.frm.doc["items"] || [], function(i, item) {
				frappe.model.round_floats_in(item);
				item.amount = flt(item.rate * item.qty, precision("amount", item));
				item.item_tax_amount = 0.0;

				$.each(["price_list_rate", "rate", "amount"], function(i, f) {
					item["base_" + f] = flt(item[f] * me.frm.doc.conversion_rate, precision("base_" + f, item));
				})
			});
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

	apply_discount_amount: function() {
		var me = this;
		var distributed_amount = 0.0;

		if (this.frm.doc.discount_amount) {
			this.frm.set_value("base_discount_amount",
				flt(this.frm.doc.discount_amount * this.frm.doc.conversion_rate, precision("base_discount_amount")))

			var grand_total_for_discount_amount = this.get_grand_total_for_discount_amount();
			// calculate item amount after Discount Amount
			if (grand_total_for_discount_amount) {
				$.each(this.frm.doc["items"] || [], function(i, item) {
					distributed_amount = flt(me.frm.doc.base_discount_amount) * item.base_amount / grand_total_for_discount_amount;
					item.base_amount = flt(item.base_amount - distributed_amount, precision("base_amount", item));
				});

				this.discount_amount_applied = true;
				this._calculate_taxes_and_totals();
			}
		} else {
			this.frm.set_value("base_discount_amount", 0);
		}
	},

	get_grand_total_for_discount_amount: function() {
		var me = this;
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
			if (value)
				total_actual_tax += value;
		});

		grand_total_for_discount_amount = flt(this.frm.doc.grand_total - total_actual_tax,
			precision("grand_total"));
		return grand_total_for_discount_amount;
	},


	determine_exclusive_rate: function() {
		if(!in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"])) return;

		var me = this;
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
				item.base_amount = flt(
					(item.amount * me.frm.doc.conversion_rate) / (1 + cumulated_tax_fraction),
					precision("base_amount", item));

				item.base_rate = flt(item.base_amount / item.qty, precision("base_rate", item));

				if(item.discount_percentage == 100) {
					item.base_price_list_rate = item.base_rate;
					item.base_rate = 0.0;
				} else {
					item.base_price_list_rate = flt(item.base_rate / (1 - item.discount_percentage / 100.0),
						precision("base_price_list_rate", item));
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
					this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_fraction_for_current_item;

			} else if(tax.charge_type == "On Previous Row Total") {
				current_tax_fraction = (tax_rate / 100.0) *
					this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			}
		}

		return current_tax_fraction;
	},

})
