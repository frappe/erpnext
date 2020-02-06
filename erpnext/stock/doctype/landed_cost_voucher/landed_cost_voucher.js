// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.LandedCostVoucher = erpnext.stock.StockController.extend({
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Payment Entry': 'Payment'
		};

		var me = this;
		this.frm.fields_dict.purchase_receipts.grid.get_field('receipt_document').get_query =
			function (doc, cdt, cdn) {
				var d = locals[cdt][cdn];

				var filters = [
					[d.receipt_document_type, 'docstatus', '=', '1'],
					[d.receipt_document_type, 'company', '=', me.frm.doc.company],
				];

				if (d.receipt_document_type == "Purchase Invoice") {
					filters.push(["Purchase Invoice", "update_stock", "=", "1"])
				}

				if (!me.frm.doc.company) frappe.msgprint(__("Please enter company first"));
				return {
					filters: filters
				}
			};

		this.frm.set_query("credit_to", function() {
			return {
				filters: {
					'account_type': 'Payable',
					'is_group': 0,
					'company': me.frm.doc.company
				}
			};
		});

		this.frm.set_query("cost_center", "items", function() {
			return {
				filters: {
					'company': me.frm.doc.company,
					"is_group": 0
				}
			}
		});

		this.frm.set_query("account_head", "taxes", function(doc) {
			var account_type = ["Tax", "Chargeable", "Expenses Included In Valuation"];
			return {
				query: "erpnext.controllers.queries.tax_account_query",
				filters: {
					"account_type": account_type,
					"company": doc.company
				}
			}
		});

		this.frm.add_fetch("receipt_document", "supplier", "supplier");
		this.frm.add_fetch("receipt_document", "posting_date", "posting_date");
		this.frm.add_fetch("receipt_document", "base_grand_total", "grand_total");
	},

	validate: function() {
		this.update_manual_distribution_json();
		this.calculate_taxes_and_totals();
	},

	refresh: function(doc) {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_dynamic_labels();

		this.show_general_ledger();

		if (doc.docstatus===1 && doc.outstanding_amount != 0 && frappe.model.can_create("Payment Entry")) {
			cur_frm.add_custom_button(__('Payment'), this.make_payment_entry, __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

		this.load_manual_distribution_data();
		this.update_manual_distribution();

		if (this.frm.doc.party && !this.frm.doc.credit_to) {
			this.party();
		}

		var help_content =
			`<br><br>
			<table class="table table-bordered" style="background-color: #f9f9f9;">
				<tr><td>
					<h4>
						<i class="fa fa-hand-right"></i>
						${__("Notes")}:
					</h4>
					<ul>
						<li>
							${__("Charges will be distributed proportionately based on item qty or amount, as per your selection")}
						</li>
						<li>
							${__("Remove item if charges is not applicable to that item")}
						</li>
						<li>
							${__("Charges are updated in Purchase Receipt against each item")}
						</li>
						<li>
							${__("Item valuation rate is recalculated considering landed cost voucher amount")}
						</li>
						<li>
							${__("Stock Ledger Entries and GL Entries are reposted for the selected Purchase Receipts")}
						</li>
					</ul>
				</td></tr>
			</table>`;

		set_field_options("landed_cost_help", help_content);
	},

	get_referenced_taxes: function() {
		var me = this;
		if(me.frm.doc.credit_to && me.frm.doc.party) {
			return frappe.call({
				method: "get_referenced_taxes",
				doc: me.frm.doc,
				callback: function(r) {
					if(r.message) {
						me.frm.doc.taxes = [];
						$.each(r.message, function(i, d) {
							var tax = me.frm.add_child("taxes");
							tax.remarks = d.remarks;
							tax.account_head = d.account_head;
							tax.amount = d.amount;
						});
						me.calculate_taxes_and_totals();
						me.update_manual_distribution();
					}
				}
			});
		}
	},

	allocate_advances_automatically: function() {
		if(this.frm.doc.allocate_advances_automatically) {
			this.get_advances();
		}
	},

	get_advances: function() {
		var me = this;
		return this.frm.call({
			method: "set_advances",
			doc: this.frm.doc,
			callback: function(r, rt) {
				refresh_field("advances");
				me.calculate_taxes_and_totals();
			}
		})
	},

	make_payment_entry: function() {
		return frappe.call({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
			args: {
				"dt": cur_frm.doc.doctype,
				"dn": cur_frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	get_items_from_purchase_receipts: function() {
		var me = this;
		if(!me.frm.doc.purchase_receipts.length) {
			frappe.msgprint(__("Please enter Purchase Receipt first"));
		} else {
			return me.frm.call({
				doc: me.frm.doc,
				method: "get_items_from_purchase_receipts",
				callback: function() {
					me.update_manual_distribution();
					me.calculate_taxes_and_totals();
					me.frm.dirty();
				}
			});
		}
	},

	amount: function(frm) {
		this.calculate_taxes_and_totals();
	},

	allocated_amount: function(frm) {
		this.calculate_taxes_and_totals();
	},

	weight: function(frm) {
		this.calculate_taxes_and_totals();
	},

	calculate_taxes_and_totals: function() {
		var me = this;

		var item_total_fields = ['qty', 'amount', 'weight'];
		$.each(item_total_fields || [], function(i, f) {
			me.frm.doc['total_' + f] = flt(frappe.utils.sum((me.frm.doc.items || []).map(d => flt(d[f]))),
				precision('total_' + f));
		});

		me.frm.doc.total_taxes_and_charges = 0;
		$.each(me.frm.doc.taxes || [], function(i, d) {
			d.amount = flt(d.amount, precision("amount", d));
			d.base_amount = flt(d.amount * me.frm.doc.conversion_rate, precision("base_amount", d));
			me.frm.doc.total_taxes_and_charges += d.amount;
		});
		me.frm.doc.total_taxes_and_charges = flt(me.frm.doc.total_taxes_and_charges, precision("total_taxes_and_charges"));
		me.frm.doc.base_total_taxes_and_charges = flt(me.frm.doc.total_taxes_and_charges * me.frm.doc.conversion_rate, precision("base_total_taxes_and_charges"));

		var total_allocated_amount = frappe.utils.sum($.map(me.frm.doc["advances"] || [], function(adv) {
			return flt(adv.allocated_amount, precision("allocated_amount", adv));
		}));

		if (me.frm.doc.party) {
			me.frm.doc.grand_total = flt(me.frm.doc.total_taxes_and_charges, precision("grand_total"));
			me.frm.doc.base_grand_total = flt(me.frm.doc.grand_total * me.frm.doc.conversion_rate, precision("base_grand_total"));
			me.frm.doc.total_advance = flt(total_allocated_amount, precision("total_advance"));
		} else {
			me.frm.doc.grand_total = 0;
			me.frm.doc.base_grand_total = 0;
			me.frm.doc.total_advance = 0;
		}

		var grand_total = me.frm.doc.party_account_currency == me.frm.doc.currency ? me.frm.doc.grand_total : me.frm.doc.base_grand_total;
		me.frm.doc.outstanding_amount = flt(grand_total - me.frm.doc.total_advance, "outstanding_amount");

		me.distribute_applicable_charges_for_item();

		me.frm.refresh_fields();
	},

	distribute_applicable_charges_for_item: function() {
		var me = this;
		var totals = {};
		var item_total_fields = ['qty', 'amount', 'weight'];
		$.each(item_total_fields || [], function(i, f) {
			totals[f] = flt(frappe.utils.sum((me.frm.doc.items || []).map(d => flt(d[f]))));
		});

		var charges_map = [];
		var manual_account_heads = new Set;
		var idx = 0;
		$.each(me.frm.doc.taxes || [], function(i, tax) {
			if (tax.base_amount) {
				var based_on = frappe.scrub(tax.distribution_criteria);

				if(based_on == "manual") {
					manual_account_heads.add(cstr(tax.account_head));
				} else {
					if(!totals[based_on]) {
						frappe.throw(__("Cannot distribute by {0} because total {0} is 0", [tax.distribution_criteria]));
					}

					charges_map[idx] = [];
					$.each(me.frm.doc.items || [], function(item_idx, item) {
						charges_map[idx][item_idx] = flt(tax.base_amount) * flt(item[based_on]) / flt(totals[based_on]);
					});
					++idx;
				}
			}
		});

		var accumulated_taxes = 0.0;
		$.each(me.frm.doc.items || [], function(item_idx, item) {
			if (item.item_code) {
				var item_total_tax = 0.0;
				for(var i = 0; i < charges_map.length; ++i) {
					item_total_tax += charges_map[i][item_idx];
				}

				Object.keys(item.manual_distribution_data).forEach(function(account_head) {
					if(manual_account_heads.has(account_head)) {
						item_total_tax += flt(item.manual_distribution_data[account_head]) * flt(me.frm.doc.conversion_rate);
					}
				});

				item.applicable_charges = item_total_tax;
				accumulated_taxes += item.applicable_charges;
			}
		});

		if (accumulated_taxes != me.frm.doc.base_total_taxes_and_charges) {
			var diff = me.frm.doc.base_total_taxes_and_charges - accumulated_taxes;
			me.frm.doc.items.slice(-1)[0].applicable_charges += diff;
		}

		refresh_field("items");
	},

	distribution_criteria: function() {
		this.update_manual_distribution();
		this.calculate_taxes_and_totals();
	},
	account_head: function() {
		this.update_manual_distribution();
	},
	taxes_add: function() {
		this.update_manual_distribution();
		this.calculate_taxes_and_totals();
	},
	taxes_remove: function() {
		this.update_manual_distribution();
		this.calculate_taxes_and_totals();
	},
	taxes_move: function() {
		this.update_manual_distribution();
	},
	items_add: function() {
		this.update_manual_distribution();
	},
	items_remove: function() {
		this.update_manual_distribution();
		this.calculate_taxes_and_totals();
	},
	items_move: function() {
		this.update_manual_distribution();
	},

	load_manual_distribution_data: function() {
		$.each(this.frm.doc.items || [], function(i, item) {
			item.manual_distribution_data = JSON.parse(item.manual_distribution || "{}");
		});
	},

	update_manual_distribution_json: function() {
		var me = this;
		$.each(me.frm.doc.items || [], function(i, item) {
			me.update_item_manual_distribution_json(i);
		});
	},

	update_item_manual_distribution_json: function(iItem) {
		//Get manual tax account heads
		var manual_taxes_cols = new Set;
		$.each(this.frm.doc.taxes || [], function(i, tax) {
			if(tax.distribution_criteria == "Manual" && tax.account_head) {
				manual_taxes_cols.add(tax.account_head);
			}
		});

		//Remove tax amounts for taxes not in manual tax set
		var item = this.frm.doc.items[iItem];
		var data = Object.assign({}, item.manual_distribution_data || {});
		Object.keys(data).forEach(function(account_head) {
			if(!manual_taxes_cols.has(account_head))
				delete data[account_head];
		});

		item.manual_distribution = JSON.stringify(data);
		this.frm.get_field("items").grid.grid_rows[iItem].refresh_field("manual_distribution");
	},

	update_manual_distribution: function() {
		var me = this;

		//Get manual tax account heads
		var manual_taxes_cols = new Set;
		$.each(me.frm.doc.taxes || [], function(i, tax) {
			if(tax.distribution_criteria == "Manual" && tax.account_head) {
				manual_taxes_cols.add(tax.account_head);
			}
		});

		//Make sure values are set in item.manual_distribution_data
		$.each(me.frm.doc.items || [], function(i, item) {
			if (manual_taxes_cols.size == 0) {
				item.manual_distribution_data = {};
			} else {
				manual_taxes_cols.forEach(function(account_head) {
					if(!item.manual_distribution_data)
						item.manual_distribution_data = {};
					if(!item.manual_distribution_data.hasOwnProperty(account_head)) {
						item.manual_distribution_data[account_head] = 0.0;
					}
				});
			}
		});

		//Get distribution data from items
		var account_heads = Array.from(manual_taxes_cols);
		var rows = [];
		var items = [];
		var row_totals = [];
		var col_totals = [];
		$.each(me.frm.doc.items || [], function(i, item) {
			if(item.item_code)
			{
				items[i] = item.item_code;
				row_totals[i] = 0.0;

				var rowdata = [];
				$.each(account_heads || [], function(j, account_head) {
					if(j >= col_totals.length)
						col_totals[j] = 0.0;

					rowdata[j] = item.manual_distribution_data[account_head];
					row_totals[i] += flt(rowdata[j]);
					col_totals[j] += flt(rowdata[j]);

					if(!rowdata[j])
						rowdata[j] = "";
				});
				rows[i] = rowdata;
			}
		});

		var editable = me.frm.doc.docstatus == 0;

		//Set table HTML
		if(account_heads.length == 0 || rows.length == 0) {
			$(me.frm.fields_dict.manual_tax_distribution.wrapper).html("");
		} else {
			var html = frappe.render_template('lcv_manual_distribution', {
				account_heads: account_heads, rows: rows, items: items, row_totals: row_totals, col_totals: col_totals,
				editable: editable
			});
			$(me.frm.fields_dict.manual_tax_distribution.wrapper).html(html);
		}

		//Listen for changes
		if(editable) {
			$("input", me.frm.fields_dict.manual_tax_distribution.wrapper).change(function() {
				var row = $(this).data("row");
				var account = $(this).data("account");
				var row_total = 0.0;
				var col_total = 0.0;

				var val = flt($(this).val(), precision("applicable_charges", me.frm.doc.items[row]));
				me.frm.doc.items[row].manual_distribution_data[account] = val;
				me.update_item_manual_distribution_json(row);
				me.frm.dirty();

				if(!val)
					val = "";
				$(this).val(val);

				$("input[data-row=" + row + "]", me.frm.fields_dict.manual_tax_distribution.wrapper).each(function() {
					col_total += flt($(this).val());
				});
				$("td[data-row=" + row + "][data-account=total]", me.frm.fields_dict.manual_tax_distribution.wrapper).text(col_total);

				$("input[data-account='" + account + "']", me.frm.fields_dict.manual_tax_distribution.wrapper).each(function() {
					row_total += flt($(this).val());
				});
				$("td[data-row=total][data-account='" + account + "']", me.frm.fields_dict.manual_tax_distribution.wrapper).text(row_total);

				me.calculate_taxes_and_totals();
			});
		}
	},

	party: function() {
		var me = this;
		frappe.run_serially([
			() => {
				if(me.frm.doc.party && me.frm.doc.company) {
					return frappe.call({
						method: "erpnext.accounts.party.get_party_account",
						args: {
							company: me.frm.doc.company,
							party_type: me.frm.doc.party_type,
							party: me.frm.doc.party,
							include_currency: true
						},
						callback: function(r) {
							if(!r.exc && r.message) {
								me.frm.set_value("credit_to", r.message);
							}
						}
					});
				}
			},
			() => {
				if (me.frm.doc.party_type == "Supplier") {
					me.frm.call({
						method: "frappe.client.get_value",
						args: {
							doctype: "Supplier",
							fieldname: "default_currency",
							filters: {name: me.frm.doc.party},
						},
						callback: function(r, rt) {
							if(r.message) {
								me.frm.set_value("currency", r.message.default_currency);
								me.set_dynamic_labels();
							}
						}
					});
				} else {
					me.frm.set_value("currency", me.get_company_currency());
					me.set_dynamic_labels();
				}
			}
		]);
	},

	get_company_currency: function() {
		return erpnext.get_currency(this.frm.doc.company);
	},

	set_dynamic_labels: function() {
		var company_currency = this.get_company_currency();

		this.frm.set_currency_labels(["base_total_taxes_and_charges", "base_grand_total"], company_currency);
		this.frm.set_currency_labels(["total_taxes_and_charges", "grand_total"], this.frm.doc.currency);
		this.frm.set_currency_labels(["outstanding_amount", "total_advance"], this.frm.doc.party_account_currency);
		this.frm.set_currency_labels(["base_amount"], company_currency, "taxes");
		this.frm.set_currency_labels(["amount"], this.frm.doc.currency, "taxes");
		this.frm.set_currency_labels(["advance_amount", "allocated_amount"], this.frm.doc.party_account_currency, "advances");

		cur_frm.set_df_property("conversion_rate", "description", "1 " + this.frm.doc.currency
			+ " = [?] " + company_currency);

		this.frm.toggle_display(["conversion_rate", "base_total_taxes_and_charges"], this.frm.doc.currency != company_currency);
		this.frm.fields_dict["taxes"].grid.set_column_disp("base_amount", this.frm.doc.currency != company_currency);

		this.frm.refresh_fields();
	},

	currency: function() {
		var transaction_date = this.frm.doc.transaction_date || this.frm.doc.posting_date;
		var me = this;
		var company_currency = this.get_company_currency();
		if(this.frm.doc.currency && this.frm.doc.currency !== company_currency) {
			this.get_exchange_rate(transaction_date, this.frm.doc.currency, company_currency,
				function(exchange_rate) {
					me.frm.set_value("conversion_rate", exchange_rate);
				});
		} else {
			this.conversion_rate();
		}
	},

	posting_date: function() {
		this.currency();
	},

	conversion_rate: function() {
		if(this.frm.doc.currency === this.get_company_currency()) {
			this.frm.doc.conversion_rate = 1.0;
		}

		if(flt(this.frm.doc.conversion_rate) > 0.0) {
			this.calculate_taxes_and_totals();
		}

		// Make read only if Accounts Settings doesn't allow stale rates
		this.frm.set_df_property("conversion_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	},

	company: function() {
		var company_currency = this.get_company_currency();
		if (!this.frm.doc.currency) {
			this.frm.set_value("currency", company_currency);
		} else {
			this.currency();
		}
		this.set_dynamic_labels();
	},

	credit_to: function() {
		var me = this;
		if(this.frm.doc.credit_to) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.credit_to },
				},
				callback: function(r, rt) {
					if(r.message) {
						me.frm.set_value("party_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				}
			});
		}
	},

	get_exchange_rate: function(transaction_date, from_currency, to_currency, callback) {
		if (!transaction_date || !from_currency || !to_currency) return;
		return frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: transaction_date,
				from_currency: from_currency,
				to_currency: to_currency,
				args: "for_buying"
			},
			callback: function(r) {
				callback(flt(r.message));
			}
		});
	},
});

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);
