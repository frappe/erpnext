// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.taxes_and_totals = class TaxesAndTotals extends erpnext.payments {
	setup() {
		this.fetch_round_off_accounts();
	}

	apply_pricing_rule_on_item(item) {
		let effective_item_rate = item.price_list_rate;
		let item_rate = item.rate;
		if (["Sales Order", "Quotation"].includes(item.parenttype) && item.blanket_order_rate) {
			effective_item_rate = item.blanket_order_rate;
		}
		if (item.margin_type == "Percentage") {
			item.rate_with_margin =
				flt(effective_item_rate) + flt(effective_item_rate) * (flt(item.margin_rate_or_amount) / 100);
		} else {
			item.rate_with_margin = flt(effective_item_rate) + flt(item.margin_rate_or_amount);
		}
		item.base_rate_with_margin = flt(item.rate_with_margin) * flt(this.frm.doc.conversion_rate);

		item_rate = flt(item.rate_with_margin, precision("rate", item));

		if (item.discount_percentage && !item.discount_amount) {
			item.discount_amount = (flt(item.rate_with_margin) * flt(item.discount_percentage)) / 100;
		}

		if (item.discount_amount > 0) {
			item_rate = flt(item.rate_with_margin - item.discount_amount, precision("rate", item));
			item.discount_percentage = (100 * flt(item.discount_amount)) / flt(item.rate_with_margin);
		}

		frappe.model.set_value(item.doctype, item.name, "rate", item_rate);
	}

	async calculate_taxes_and_totals(update_paid_amount) {
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();
		this.calculate_discount_amount();

		// # Update grand total as per cash and non trade discount
		if (this.frm.doc.apply_discount_on == "Grand Total" && this.frm.doc.is_cash_or_non_trade_discount) {
			this.frm.doc.grand_total -= this.frm.doc.discount_amount;
			this.frm.doc.base_grand_total -= this.frm.doc.base_discount_amount;
			this.frm.doc.rounding_adjustment = 0;
			this.frm.doc.base_rounding_adjustment = 0;
			this.set_rounded_total();
		}

		await this.calculate_shipping_charges();

		// Advance calculation applicable to Sales/Purchase Invoice
		if (
			["Sales Invoice", "POS Invoice", "Purchase Invoice"].includes(this.frm.doc.doctype) &&
			this.frm.doc.docstatus < 2 &&
			!this.frm.doc.is_return
		) {
			this.calculate_total_advance(update_paid_amount);
		}

		if (
			["Sales Invoice", "POS Invoice"].includes(this.frm.doc.doctype) &&
			this.frm.doc.is_pos &&
			this.frm.doc.is_return
		) {
			await this.set_total_amount_to_default_mop();
			this.calculate_paid_amount();
		}

		// Sales person's commission
		if (["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"].includes(this.frm.doc.doctype)) {
			this.calculate_commission();
			this.calculate_contribution();
		}

		// Update paid amount on return/debit note creation
		if (
			this.frm.doc.doctype === "Purchase Invoice" &&
			this.frm.doc.is_return &&
			this.frm.doc.grand_total < 0 &&
			this.frm.doc.grand_total > this.frm.doc.paid_amount
		) {
			this.frm.doc.paid_amount = flt(this.frm.doc.grand_total, precision("grand_total"));
		}

		this.frm.refresh_fields();
	}

	calculate_discount_amount() {
		if (frappe.meta.get_docfield(this.frm.doc.doctype, "discount_amount")) {
			this.set_discount_amount();
			this.apply_discount_amount();
		}
	}

	_calculate_taxes_and_totals() {
		const is_quotation = this.frm.doc.doctype == "Quotation";
		this.frm._items = is_quotation ? this.filtered_items() : this.frm.doc.items;

		this.validate_conversion_rate();
		this.calculate_item_values();
		this.initialize_taxes();
		this.determine_exclusive_rate();
		this.calculate_net_total();
		this.calculate_taxes();
		this.adjust_grand_total_for_inclusive_tax();
		this.calculate_totals();
		this._cleanup();
	}

	validate_conversion_rate() {
		this.frm.doc.conversion_rate = flt(
			this.frm.doc.conversion_rate,
			cur_frm ? precision("conversion_rate") : 9
		);
		var conversion_rate_label = frappe.meta.get_label(
			this.frm.doc.doctype,
			"conversion_rate",
			this.frm.doc.name
		);
		var company_currency = this.get_company_currency();

		if (!this.frm.doc.conversion_rate) {
			if (this.frm.doc.currency == company_currency) {
				this.frm.set_value("conversion_rate", 1);
			} else {
				const subs = [conversion_rate_label, this.frm.doc.currency, company_currency];
				const err_message = __(
					"{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}",
					subs
				);
				frappe.throw(err_message);
			}
		}
	}

	calculate_item_values() {
		var me = this;
		if (!this.discount_amount_applied) {
			for (const item of this.frm.doc.items || []) {
				frappe.model.round_floats_in(item);
				item.net_rate = item.rate;
				item.qty = item.qty === undefined ? (me.frm.doc.is_return ? -1 : 1) : item.qty;

				if (!(me.frm.doc.is_return || me.frm.doc.is_debit_note)) {
					item.net_amount = item.amount = flt(item.rate * item.qty, precision("amount", item));
				} else {
					// allow for '0' qty on Credit/Debit notes
					let qty = flt(item.qty);
					if (!qty) {
						qty = me.frm.doc.is_debit_note ? 1 : -1;
						if (me.frm.doc.doctype !== "Purchase Receipt" && me.frm.doc.is_return === 1) {
							// In case of Purchase Receipt, qty can be 0 if all items are rejected
							qty = flt(item.qty);
						}
					}

					item.net_amount = item.amount = flt(item.rate * qty, precision("amount", item));
				}

				item.item_tax_amount = 0.0;
				item.total_weight = flt(item.weight_per_unit * item.stock_qty);

				me.set_in_company_currency(item, [
					"price_list_rate",
					"rate",
					"amount",
					"net_rate",
					"net_amount",
				]);
			}
		}
	}

	set_in_company_currency(doc, fields) {
		var me = this;
		$.each(fields, function (i, f) {
			doc["base_" + f] = flt(
				flt(doc[f], precision(f, doc)) * me.frm.doc.conversion_rate,
				precision("base_" + f, doc)
			);
		});
	}

	initialize_taxes() {
		var me = this;

		$.each(this.frm.doc["taxes"] || [], function (i, tax) {
			if (!tax.dont_recompute_tax) {
				tax.item_wise_tax_detail = {};
			}
			var tax_fields = [
				"total",
				"tax_amount_after_discount_amount",
				"tax_amount_for_current_item",
				"grand_total_for_current_item",
				"tax_fraction_for_current_item",
				"grand_total_fraction_for_current_item",
			];

			if (
				cstr(tax.charge_type) != "Actual" &&
				!(me.discount_amount_applied && me.frm.doc.apply_discount_on == "Grand Total")
			) {
				tax_fields.push("tax_amount");
			}

			$.each(tax_fields, function (i, fieldname) {
				tax[fieldname] = 0.0;
			});

			if (!this.discount_amount_applied) {
				erpnext.accounts.taxes.validate_taxes_and_charges(tax.doctype, tax.name);
				erpnext.accounts.taxes.validate_inclusive_tax(tax, this.frm);
			}
			frappe.model.round_floats_in(tax);
		});
	}

	fetch_round_off_accounts() {
		let me = this;
		frappe.flags.round_off_applicable_accounts = [];

		if (me.frm.doc.company) {
			frappe.call({
				method: "erpnext.controllers.taxes_and_totals.get_round_off_applicable_accounts",
				args: {
					company: me.frm.doc.company,
					account_list: frappe.flags.round_off_applicable_accounts,
				},
				callback(r) {
					if (r.message) {
						frappe.flags.round_off_applicable_accounts.push(...r.message);
					}
				},
			});
		}

		frappe.call({
			method: "erpnext.controllers.taxes_and_totals.get_rounding_tax_settings",
			callback: function (r) {
				frappe.flags.round_off_settings = r.message;
			},
		});
	}

	determine_exclusive_rate() {
		var me = this;

		var has_inclusive_tax = false;
		$.each(me.frm.doc["taxes"] || [], function (i, row) {
			if (cint(row.included_in_print_rate)) has_inclusive_tax = true;
		});
		if (has_inclusive_tax == false) return;

		$.each(this.frm.doc.items || [], function (n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			var cumulated_tax_fraction = 0.0;
			var total_inclusive_tax_amount_per_qty = 0;
			$.each(me.frm.doc["taxes"] || [], function (i, tax) {
				var current_tax_fraction = me.get_current_tax_fraction(tax, item_tax_map);
				tax.tax_fraction_for_current_item = current_tax_fraction[0];
				var inclusive_tax_amount_per_qty = current_tax_fraction[1];

				if (i == 0) {
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item;
				} else {
					tax.grand_total_fraction_for_current_item =
						me.frm.doc["taxes"][i - 1].grand_total_fraction_for_current_item +
						tax.tax_fraction_for_current_item;
				}

				cumulated_tax_fraction += tax.tax_fraction_for_current_item;
				total_inclusive_tax_amount_per_qty += inclusive_tax_amount_per_qty * flt(item.qty);
			});

			if (
				!me.discount_amount_applied &&
				item.qty &&
				(total_inclusive_tax_amount_per_qty || cumulated_tax_fraction)
			) {
				var amount = flt(item.amount) - total_inclusive_tax_amount_per_qty;
				item.net_amount = flt(amount / (1 + cumulated_tax_fraction), precision("net_amount", item));
				item.net_rate = item.qty ? flt(item.net_amount / item.qty, precision("net_rate", item)) : 0;

				me.set_in_company_currency(item, ["net_rate", "net_amount"]);
			}
		});
	}

	get_current_tax_fraction(tax, item_tax_map) {
		// Get tax fraction for calculating tax exclusive amount
		// from tax inclusive amount
		var current_tax_fraction = 0.0;
		var inclusive_tax_amount_per_qty = 0;

		if (cint(tax.included_in_print_rate)) {
			var tax_rate = this._get_tax_rate(tax, item_tax_map);

			if (tax.charge_type == "On Net Total") {
				current_tax_fraction = tax_rate / 100.0;
			} else if (tax.charge_type == "On Previous Row Amount") {
				current_tax_fraction =
					(tax_rate / 100.0) *
					this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_fraction_for_current_item;
			} else if (tax.charge_type == "On Previous Row Total") {
				current_tax_fraction =
					(tax_rate / 100.0) *
					this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			} else if (tax.charge_type == "On Item Quantity") {
				inclusive_tax_amount_per_qty = flt(tax_rate);
			}
		}

		if (tax.add_deduct_tax && tax.add_deduct_tax == "Deduct") {
			current_tax_fraction *= -1;
			inclusive_tax_amount_per_qty *= -1;
		}
		return [current_tax_fraction, inclusive_tax_amount_per_qty];
	}

	_get_tax_rate(tax, item_tax_map) {
		return Object.keys(item_tax_map).indexOf(tax.account_head) != -1
			? flt(item_tax_map[tax.account_head], precision("rate", tax))
			: tax.rate;
	}

	calculate_net_total() {
		var me = this;
		this.frm.doc.total_qty =
			this.frm.doc.total =
			this.frm.doc.base_total =
			this.frm.doc.net_total =
			this.frm.doc.base_net_total =
				0.0;

		$.each(this.frm._items || [], function (i, item) {
			me.frm.doc.total += item.amount;
			me.frm.doc.total_qty += item.qty;
			me.frm.doc.base_total += item.base_amount;
			me.frm.doc.net_total += item.net_amount;
			me.frm.doc.base_net_total += item.base_net_amount;
		});

		frappe.model.round_floats_in(this.frm.doc, ["total", "base_total", "net_total", "base_net_total"]);
	}

	calculate_shipping_charges() {
		// Do not apply shipping rule for POS
		if (this.frm.doc.is_pos) {
			return;
		}

		frappe.model.round_floats_in(this.frm.doc, ["total", "base_total", "net_total", "base_net_total"]);
		if (frappe.meta.get_docfield(this.frm.doc.doctype, "shipping_rule", this.frm.doc.name)) {
			return this.shipping_rule();
		}
	}

	add_taxes_from_item_tax_template(item_tax_map) {
		let me = this;

		if (item_tax_map && cint(frappe.defaults.get_default("add_taxes_from_item_tax_template"))) {
			if (typeof item_tax_map == "string") {
				item_tax_map = JSON.parse(item_tax_map);
			}

			$.each(item_tax_map, function (tax, rate) {
				let found = (me.frm.doc.taxes || []).find((d) => d.account_head === tax);
				if (!found) {
					let child = frappe.model.add_child(me.frm.doc, "taxes");
					child.charge_type = "On Net Total";
					child.account_head = tax;
					child.rate = 0;
					child.set_by_item_tax_template = true;
				}
			});
		}
	}

	calculate_taxes() {
		const doc = this.frm.doc;
		if (!doc.taxes?.length) return;

		var me = this;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(doc.taxes, function (i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(this.frm._items || [], function (n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			$.each(doc.taxes, function (i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);
				if (frappe.flags.round_row_wise_tax) {
					current_tax_amount = flt(current_tax_amount, precision("tax_amount", tax));
				}

				// Adjust divisional loss to the last item
				if (tax.charge_type == "Actual") {
					actual_tax_dict[tax.idx] -= current_tax_amount;
					if (n == me.frm._items.length - 1) {
						current_tax_amount += actual_tax_dict[tax.idx];
					}
				}

				// accumulate tax amount into tax.tax_amount
				if (
					tax.charge_type != "Actual" &&
					!(me.discount_amount_applied && me.frm.doc.apply_discount_on == "Grand Total")
				) {
					tax.tax_amount += current_tax_amount;
				}

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// tax amount after discount amount
				tax.tax_amount_after_discount_amount += current_tax_amount;

				// for buying
				if (tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = tax.category == "Valuation" ? 0.0 : current_tax_amount;

					current_tax_amount *= tax.add_deduct_tax == "Deduct" ? -1.0 : 1.0;
				}

				// note: grand_total_for_current_item contains the contribution of
				// item's amount, previously applied tax and the current tax on that item
				if (i == 0) {
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount);
				} else {
					tax.grand_total_for_current_item = flt(
						me.frm.doc["taxes"][i - 1].grand_total_for_current_item + current_tax_amount
					);
				}
			});
		});

		const discount_amount_applied = this.discount_amount_applied;
		if (
			doc.apply_discount_on === "Grand Total" &&
			(discount_amount_applied || doc.discount_amount || doc.additional_discount_percentage)
		) {
			const tax_amount_precision = precision("tax_amount", doc.taxes[0]);

			for (const [i, tax] of doc.taxes.entries()) {
				if (discount_amount_applied)
					tax.tax_amount_after_discount_amount = flt(
						tax.tax_amount_after_discount_amount,
						tax_amount_precision
					);

				this.set_cumulative_total(i, tax);
			}

			if (!this.discount_amount_applied) {
				this.grand_total_for_distributing_discount = doc.taxes[doc.taxes.length - 1].total;
			} else {
				this.grand_total_diff = flt(
					this.grand_total_for_distributing_discount -
						doc.discount_amount -
						doc.taxes[doc.taxes.length - 1].total,
					precision("grand_total")
				);
			}
		}

		for (const [i, tax] of doc.taxes.entries()) {
			me.round_off_totals(tax);
			me.set_in_company_currency(tax, ["tax_amount", "tax_amount_after_discount_amount"]);

			me.round_off_base_values(tax);

			// in tax.total, accumulate grand total for each tax
			me.set_cumulative_total(i, tax);

			me.set_in_company_currency(tax, ["total"]);
		}
	}

	set_cumulative_total(row_idx, tax) {
		var tax_amount = tax.tax_amount_after_discount_amount;
		if (tax.category == "Valuation") {
			tax_amount = 0;
		}

		if (tax.add_deduct_tax == "Deduct") {
			tax_amount = -1 * tax_amount;
		}

		if (row_idx == 0) {
			tax.total = flt(this.frm.doc.net_total + tax_amount, precision("total", tax));
		} else {
			tax.total = flt(this.frm.doc["taxes"][row_idx - 1].total + tax_amount, precision("total", tax));
		}
	}

	_load_item_tax_rate(item_tax_rate) {
		return item_tax_rate ? JSON.parse(item_tax_rate) : {};
	}

	get_current_tax_amount(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;
		var current_net_amount = 0.0;

		// To set row_id by default as previous row.
		if (["On Previous Row Amount", "On Previous Row Total"].includes(tax.charge_type)) {
			if (tax.idx === 1) {
				frappe.throw(
					__(
						"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
					)
				);
			}
			if (!tax.row_id) {
				tax.row_id = tax.idx - 1;
			}
		}
		if (tax.charge_type == "Actual") {
			current_net_amount = item.net_amount;
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total
				? (item.net_amount / this.frm.doc.net_total) * actual
				: 0.0;
		} else if (tax.charge_type == "On Net Total") {
			if (tax.account_head in item_tax_map) {
				current_net_amount = item.net_amount;
			}
			current_tax_amount = (tax_rate / 100.0) * item.net_amount;
		} else if (tax.charge_type == "On Previous Row Amount") {
			current_net_amount = this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;
			current_tax_amount =
				(tax_rate / 100.0) * this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;
		} else if (tax.charge_type == "On Previous Row Total") {
			current_net_amount = this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
			current_tax_amount =
				(tax_rate / 100.0) * this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		} else if (tax.charge_type == "On Item Quantity") {
			// don't sum current net amount due to the field being a currency field
			current_tax_amount = tax_rate * item.qty;
		}

		return current_tax_amount;
	}

	round_off_totals(tax) {
		if (frappe.flags.round_off_applicable_accounts.includes(tax.account_head)) {
			tax.tax_amount = Math.round(tax.tax_amount);
			tax.tax_amount_after_discount_amount = Math.round(tax.tax_amount_after_discount_amount);
		}

		tax.tax_amount = flt(tax.tax_amount, precision("tax_amount", tax));
		tax.tax_amount_after_discount_amount = flt(
			tax.tax_amount_after_discount_amount,
			precision("tax_amount", tax)
		);
	}

	round_off_base_values(tax) {
		if (frappe.flags.round_off_applicable_accounts.includes(tax.account_head)) {
			tax.base_tax_amount = Math.round(tax.base_tax_amount);
			tax.base_tax_amount_after_discount_amount = Math.round(tax.base_tax_amount_after_discount_amount);
		}
	}

	/**
	 * @deprecated Use adjust_grand_total_for_inclusive_tax instead.
	 */
	manipulate_grand_total_for_inclusive_tax() {
		// for backward compatablility - if in case used by an external application
		this.adjust_grand_total_for_inclusive_tax();
	}

	adjust_grand_total_for_inclusive_tax() {
		var me = this;

		// if any inclusive taxes and diff
		if (this.frm.doc["taxes"] && this.frm.doc["taxes"].length) {
			var any_inclusive_tax = false;
			$.each(this.frm.doc.taxes || [], function (i, d) {
				if (cint(d.included_in_print_rate)) any_inclusive_tax = true;
			});
			if (any_inclusive_tax) {
				var last_tax = me.frm.doc["taxes"].slice(-1)[0];
				var non_inclusive_tax_amount = frappe.utils.sum(
					$.map(this.frm.doc.taxes || [], function (d) {
						if (!d.included_in_print_rate) {
							let tax_amount =
								d.category === "Valuation" ? 0 : d.tax_amount_after_discount_amount;
							if (d.add_deduct_tax === "Deduct") tax_amount *= -1;
							return tax_amount;
						}
					})
				);
				var diff =
					me.frm.doc.total +
					non_inclusive_tax_amount -
					flt(last_tax.total, precision("grand_total"));

				if (me.discount_amount_applied && me.frm.doc.discount_amount) {
					diff -= flt(me.frm.doc.discount_amount);
				}

				diff = flt(diff, precision("rounding_adjustment"));

				if (diff && Math.abs(diff) <= 5.0 / Math.pow(10, precision("tax_amount", last_tax))) {
					me.grand_total_diff = diff;
				}
			}
		}
	}

	calculate_totals() {
		// Changing sequence can cause rounding_adjustmentng issue and on-screen discrepency
		const me = this;
		const tax_count = this.frm.doc.taxes?.length;
		const grand_total_diff = this.grand_total_diff || 0;

		this.frm.doc.grand_total = flt(
			tax_count ? this.frm.doc["taxes"][tax_count - 1].total + grand_total_diff : this.frm.doc.net_total
		);

		if (
			["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice"].includes(
				this.frm.doc.doctype
			)
		) {
			this.frm.doc.base_grand_total = this.frm.doc.total_taxes_and_charges
				? flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate)
				: this.frm.doc.base_net_total;
		} else {
			// other charges added/deducted
			this.frm.doc.taxes_and_charges_added = this.frm.doc.taxes_and_charges_deducted = 0.0;
			if (tax_count) {
				$.each(this.frm.doc["taxes"] || [], function (i, tax) {
					if (["Valuation and Total", "Total"].includes(tax.category)) {
						if (tax.add_deduct_tax == "Add") {
							me.frm.doc.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount);
						} else {
							me.frm.doc.taxes_and_charges_deducted += flt(
								tax.tax_amount_after_discount_amount
							);
						}
					}
				});

				frappe.model.round_floats_in(this.frm.doc, [
					"taxes_and_charges_added",
					"taxes_and_charges_deducted",
				]);
			}

			this.frm.doc.base_grand_total = flt(
				this.frm.doc.taxes_and_charges_added || this.frm.doc.taxes_and_charges_deducted
					? flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate)
					: this.frm.doc.base_net_total
			);

			this.set_in_company_currency(this.frm.doc, [
				"taxes_and_charges_added",
				"taxes_and_charges_deducted",
			]);
		}

		this.frm.doc.total_taxes_and_charges = flt(
			this.frm.doc.grand_total - this.frm.doc.net_total - grand_total_diff,
			precision("total_taxes_and_charges")
		);

		this.set_in_company_currency(this.frm.doc, ["total_taxes_and_charges"]);

		// Round grand total as per precision
		frappe.model.round_floats_in(this.frm.doc, ["grand_total", "base_grand_total"]);

		// rounded totals
		this.set_rounded_total();
	}

	set_rounded_total() {
		var disable_rounded_total = 0;
		if (frappe.meta.get_docfield(this.frm.doc.doctype, "disable_rounded_total", this.frm.doc.name)) {
			disable_rounded_total = this.frm.doc.disable_rounded_total;
		} else if (frappe.sys_defaults.disable_rounded_total) {
			disable_rounded_total = frappe.sys_defaults.disable_rounded_total;
		}

		if (cint(disable_rounded_total)) {
			this.frm.doc.rounded_total = 0;
			this.frm.doc.base_rounded_total = 0;
			this.frm.doc.rounding_adjustment = 0;
			return;
		}

		if (frappe.meta.get_docfield(this.frm.doc.doctype, "rounded_total", this.frm.doc.name)) {
			this.frm.doc.rounded_total = round_based_on_smallest_currency_fraction(
				this.frm.doc.grand_total,
				this.frm.doc.currency,
				precision("rounded_total")
			);
			this.frm.doc.rounding_adjustment = flt(
				this.frm.doc.rounded_total - this.frm.doc.grand_total,
				precision("rounding_adjustment")
			);

			this.set_in_company_currency(this.frm.doc, ["rounding_adjustment", "rounded_total"]);
		}
	}

	_cleanup() {
		this.frm.doc.base_in_words = this.frm.doc.in_words = "";
		let items = this.frm.doc.items;

		if (items && items.length) {
			if (!frappe.meta.get_docfield(items[0].doctype, "item_tax_amount", this.frm.doctype)) {
				$.each(items || [], function (i, item) {
					delete item["item_tax_amount"];
				});
			}
		}

		if (this.frm.doc["taxes"] && this.frm.doc["taxes"].length) {
			var temporary_fields = [
				"tax_amount_for_current_item",
				"grand_total_for_current_item",
				"tax_fraction_for_current_item",
				"grand_total_fraction_for_current_item",
			];

			if (
				!frappe.meta.get_docfield(
					this.frm.doc["taxes"][0].doctype,
					"tax_amount_after_discount_amount",
					this.frm.doctype
				)
			) {
				temporary_fields.push("tax_amount_after_discount_amount");
			}

			$.each(this.frm.doc["taxes"] || [], function (i, tax) {
				$.each(temporary_fields, function (i, fieldname) {
					delete tax[fieldname];
				});
			});
		}
	}

	set_discount_amount() {
		if (this.frm.doc.additional_discount_percentage) {
			this.frm.doc.discount_amount = flt(
				(flt(this.frm.doc[frappe.scrub(this.frm.doc.apply_discount_on)]) *
					this.frm.doc.additional_discount_percentage) /
					100,
				precision("discount_amount")
			);
		}
	}

	apply_discount_amount() {
		var me = this;
		var distributed_amount = 0.0;
		this.frm.doc.base_discount_amount = 0.0;

		if (this.frm.doc.discount_amount) {
			if (!this.frm.doc.apply_discount_on) frappe.throw(__("Please select Apply Discount On"));

			this.frm.doc.base_discount_amount = flt(
				this.frm.doc.discount_amount * this.frm.doc.conversion_rate,
				precision("base_discount_amount")
			);

			if (
				this.frm.doc.apply_discount_on == "Grand Total" &&
				this.frm.doc.is_cash_or_non_trade_discount
			) {
				return;
			}

			const total_for_discount_amount = this.get_total_for_discount_amount();
			let net_total = 0;
			let expected_net_total = 0;

			// calculate item amount after Discount Amount
			if (total_for_discount_amount) {
				$.each(this.frm._items || [], function (i, item) {
					distributed_amount =
						(flt(me.frm.doc.discount_amount) * item.net_amount) / total_for_discount_amount;

					const adjusted_net_amount = item.net_amount - distributed_amount;
					expected_net_total += adjusted_net_amount;
					item.net_amount = flt(adjusted_net_amount, precision("net_amount", item));
					net_total += item.net_amount;

					// discount amount rounding adjustment
					// assignment to rounding_difference is intentional
					const rounding_difference = flt(expected_net_total - net_total, precision("net_total"));
					if (rounding_difference) {
						item.net_amount = flt(
							item.net_amount + rounding_difference,
							precision("net_amount", item)
						);
						net_total += rounding_difference;
					}
					item.net_rate = item.qty
						? flt(item.net_amount / item.qty, precision("net_rate", item))
						: 0;
					me.set_in_company_currency(item, ["net_rate", "net_amount"]);
				});

				this.discount_amount_applied = true;
				this._calculate_taxes_and_totals();
			}
		}
	}

	get_total_for_discount_amount() {
		const doc = this.frm.doc;

		if (doc.apply_discount_on == "Net Total" || !doc.taxes?.length) return doc.net_total;

		let total_actual_tax = 0.0;
		let actual_taxes_dict = {};

		function update_actual_taxes_dict(tax, tax_amount) {
			if (tax.add_deduct_tax == "Deduct") tax_amount *= -1;
			if (tax.category != "Valuation") total_actual_tax += tax_amount;

			actual_taxes_dict[tax.idx] = {
				tax_amount: tax_amount,
				cumulative_total: total_actual_tax,
			};
		}

		doc.taxes.forEach((tax) => {
			if (["Actual", "On Item Quantity"].includes(tax.charge_type)) {
				update_actual_taxes_dict(tax, tax.tax_amount);
				return;
			}

			const base_row = actual_taxes_dict[tax.row_id];
			if (!base_row) return;

			// if charge type is 'On Previous Row Amount', calculate tax on previous row amount
			// else (On Previous Row Total) calculate tax on cumulative total
			const base_tax_amount =
				tax.charge_type == "On Previous Row Amount"
					? base_row["tax_amount"]
					: base_row["cumulative_total"];
			update_actual_taxes_dict(tax, (base_tax_amount * tax.rate) / 100);
		});

		return (this.grand_total_for_distributing_discount || doc.grand_total) - total_actual_tax;
	}

	calculate_total_advance(update_paid_amount) {
		var total_allocated_amount = frappe.utils.sum(
			$.map(this.frm.doc["advances"] || [], function (adv) {
				return flt(adv.allocated_amount, precision("allocated_amount", adv));
			})
		);
		this.frm.doc.total_advance = flt(total_allocated_amount, precision("total_advance"));

		if (this.frm.doc.write_off_outstanding_amount_automatically) {
			this.frm.doc.write_off_amount = 0;
		}

		this.calculate_outstanding_amount(update_paid_amount);
		this.calculate_write_off_amount();
	}

	is_internal_invoice() {
		if (["Sales Invoice", "Purchase Invoice"].includes(this.frm.doc.doctype)) {
			if (this.frm.doc.company === this.frm.doc.represents_company) {
				return true;
			}
		}
		return false;
	}

	calculate_outstanding_amount(update_paid_amount) {
		// NOTE:
		// paid_amount and write_off_amount is only for POS/Loyalty Point Redemption Invoice
		// total_advance is only for non POS Invoice
		if (["Sales Invoice", "POS Invoice"].includes(this.frm.doc.doctype) && this.frm.doc.is_return) {
			this.calculate_paid_amount();
		}

		if (this.frm.doc.is_return || this.frm.doc.docstatus > 0 || this.is_internal_invoice()) return;

		frappe.model.round_floats_in(this.frm.doc, ["grand_total", "total_advance", "write_off_amount"]);

		if (["Sales Invoice", "POS Invoice", "Purchase Invoice"].includes(this.frm.doc.doctype)) {
			let grand_total = this.frm.doc.rounded_total || this.frm.doc.grand_total;
			let base_grand_total = this.frm.doc.base_rounded_total || this.frm.doc.base_grand_total;

			if (this.frm.doc.party_account_currency == this.frm.doc.currency) {
				var total_amount_to_pay = flt(
					grand_total - this.frm.doc.total_advance - this.frm.doc.write_off_amount,
					precision("grand_total")
				);
			} else {
				var total_amount_to_pay = flt(
					flt(base_grand_total, precision("base_grand_total")) -
						this.frm.doc.total_advance -
						this.frm.doc.base_write_off_amount,
					precision("base_grand_total")
				);
			}

			frappe.model.round_floats_in(this.frm.doc, ["paid_amount"]);
			this.set_in_company_currency(this.frm.doc, ["paid_amount"]);

			if (this.frm.refresh_field) {
				this.frm.refresh_field("paid_amount");
				this.frm.refresh_field("base_paid_amount");
			}

			if (["Sales Invoice", "POS Invoice"].includes(this.frm.doc.doctype)) {
				let total_amount_for_payment =
					this.frm.doc.redeem_loyalty_points && this.frm.doc.loyalty_amount
						? flt(
								total_amount_to_pay - this.frm.doc.loyalty_amount,
								precision("base_grand_total")
						  )
						: total_amount_to_pay;
				this.set_default_payment(total_amount_for_payment, update_paid_amount);
				this.calculate_paid_amount();
			}
			this.calculate_change_amount();

			var paid_amount =
				this.frm.doc.party_account_currency == this.frm.doc.currency
					? this.frm.doc.paid_amount
					: this.frm.doc.base_paid_amount;
			this.frm.doc.outstanding_amount = flt(
				total_amount_to_pay -
					flt(paid_amount) +
					flt(this.frm.doc.change_amount * this.frm.doc.conversion_rate),
				precision("outstanding_amount")
			);
		}
	}

	async set_total_amount_to_default_mop() {
		let grand_total = this.frm.doc.rounded_total || this.frm.doc.grand_total;
		let base_grand_total = this.frm.doc.base_rounded_total || this.frm.doc.base_grand_total;

		if (this.frm.doc.party_account_currency == this.frm.doc.currency) {
			var total_amount_to_pay = flt(
				grand_total - this.frm.doc.total_advance - this.frm.doc.write_off_amount,
				precision("grand_total")
			);
		} else {
			var total_amount_to_pay = flt(
				flt(base_grand_total, precision("base_grand_total")) -
					this.frm.doc.total_advance -
					this.frm.doc.base_write_off_amount,
				precision("base_grand_total")
			);
		}

		/*
		During returns, if an user select mode of payment other than
		default mode of payment, it should retain the user selection
		instead resetting it to default mode of payment.
		*/

		let payment_amount = 0;
		this.frm.doc.payments.forEach((payment) => {
			payment_amount += payment.amount;
		});

		if (payment_amount == total_amount_to_pay) {
			return;
		}

		/*
		For partial return, if the payment was made using single mode of payment
		it should set the return to that mode of payment only.
		*/

		if (this.frm.doc.return_against) {
			let { message: return_against_mop } = await frappe.call({
				method: "erpnext.controllers.sales_and_purchase_return.get_payment_data",
				args: {
					invoice: this.frm.doc.return_against,
				},
			});

			if (return_against_mop.length === 1) {
				this.frm.doc.payments.forEach((payment) => {
					if (payment.mode_of_payment == return_against_mop[0].mode_of_payment) {
						payment.amount = total_amount_to_pay;
					} else {
						payment.amount = 0;
					}
				});
				this.frm.refresh_fields();
				return;
			}
		}

		this.frm.doc.payments.find((payment) => {
			if (payment.default) {
				payment.amount = total_amount_to_pay;
			} else {
				payment.amount = 0;
			}
		});

		this.frm.refresh_fields();
	}

	set_default_payment(total_amount_to_pay, update_paid_amount) {
		var me = this;
		var payment_status = true;

		if (
			this.frm.doc.is_pos &&
			cint(this.frm.set_default_payment) &&
			(update_paid_amount === undefined || update_paid_amount)
		) {
			$.each(this.frm.doc["payments"] || [], function (index, data) {
				if (data.default && payment_status && total_amount_to_pay > 0) {
					let base_amount, amount;

					if (me.frm.doc.party_account_currency == me.frm.doc.currency) {
						// if customer/supplier currency is same as company currency
						// total_amount_to_pay is already in customer/supplier currency
						// so base_amount has to be calculated using total_amount_to_pay
						base_amount = flt(
							total_amount_to_pay * me.frm.doc.conversion_rate,
							precision("base_amount", data)
						);
						amount = flt(total_amount_to_pay, precision("amount", data));
					} else {
						base_amount = flt(total_amount_to_pay, precision("base_amount", data));
						amount = flt(
							total_amount_to_pay / me.frm.doc.conversion_rate,
							precision("amount", data)
						);
					}

					frappe.model.set_value(data.doctype, data.name, "base_amount", base_amount);
					frappe.model.set_value(data.doctype, data.name, "amount", amount);
					payment_status = false;
				} else if (me.frm.doc.paid_amount) {
					frappe.model.set_value(data.doctype, data.name, "amount", 0.0);
				}
			});
		}
	}

	calculate_paid_amount() {
		var me = this;
		var paid_amount = 0.0;
		var base_paid_amount = 0.0;
		if (this.frm.doc.is_pos) {
			$.each(this.frm.doc["payments"] || [], function (index, data) {
				data.base_amount = flt(
					data.amount * me.frm.doc.conversion_rate,
					precision("base_amount", data)
				);
				paid_amount += data.amount;
				base_paid_amount += data.base_amount;
			});
		} else if (!this.frm.doc.is_return) {
			this.frm.doc.payments = [];
		}
		if (this.frm.doc.redeem_loyalty_points && this.frm.doc.loyalty_amount) {
			base_paid_amount += this.frm.doc.loyalty_amount;
			paid_amount += flt(
				this.frm.doc.loyalty_amount / me.frm.doc.conversion_rate,
				precision("paid_amount")
			);
		}

		this.frm.set_value("paid_amount", flt(paid_amount, precision("paid_amount")));
		this.frm.set_value("base_paid_amount", flt(base_paid_amount, precision("base_paid_amount")));
	}

	calculate_change_amount() {
		this.frm.doc.change_amount = 0.0;
		this.frm.doc.base_change_amount = 0.0;
		if (
			["Sales Invoice", "POS Invoice"].includes(this.frm.doc.doctype) &&
			this.frm.doc.paid_amount > this.frm.doc.grand_total &&
			!this.frm.doc.is_return
		) {
			var payment_types = $.map(this.frm.doc.payments, function (d) {
				return d.type;
			});
			if (in_list(payment_types, "Cash")) {
				var grand_total = this.frm.doc.rounded_total || this.frm.doc.grand_total;
				var base_grand_total = this.frm.doc.base_rounded_total || this.frm.doc.base_grand_total;

				this.frm.doc.change_amount = flt(
					this.frm.doc.paid_amount - grand_total,
					precision("change_amount")
				);

				this.frm.doc.base_change_amount = flt(
					this.frm.doc.base_paid_amount - base_grand_total,
					precision("base_change_amount")
				);
			}
		}
	}

	calculate_write_off_amount() {
		if (this.frm.doc.write_off_outstanding_amount_automatically) {
			this.frm.doc.write_off_amount = flt(
				this.frm.doc.outstanding_amount,
				precision("write_off_amount")
			);
			this.frm.doc.base_write_off_amount = flt(
				this.frm.doc.write_off_amount * this.frm.doc.conversion_rate,
				precision("base_write_off_amount")
			);

			this.calculate_outstanding_amount(false);
		}
	}

	filtered_items() {
		return this.frm.doc.items.filter((item) => !item["is_alternative"]);
	}
};
