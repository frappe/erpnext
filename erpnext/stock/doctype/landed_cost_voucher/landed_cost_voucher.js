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

		this.frm.fields_dict["credit_to"].get_query = function() {
			return {
				filters: {
					'account_type': 'Payable',
					'is_group': 0,
					'company': me.frm.doc.company,
					'account_currency': erpnext.get_currency(me.frm.doc.company)
				}
			};
		};

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

	before_submit: function() {
		this.validate_manual_distribution_totals();

		var manual_taxes_cols = new Set;
		$.each(me.frm.doc.taxes || [], function(i, tax) {
			if(tax.distribution_criteria == "Manual" && tax.account_head) {
				manual_taxes_cols.add(tax.account_head);
			}
		});
	},

	validate: function() {
		this.update_manual_distribution_json();
		this.calculate_taxes_and_totals();
		this.set_applicable_charges_for_item();
	},

	refresh: function(doc) {
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
						me.frm.refresh_field("taxes");
						me.update_manual_distribution();
						me.calculate_taxes_and_totals();
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
		if(!this.frm.doc.purchase_receipts.length) {
			frappe.msgprint(__("Please enter Purchase Receipt first"));
		} else {
			return me.frm.call({
				doc: me.frm.doc,
				method: "get_items_from_purchase_receipts",
				callback: function() {
					me.frm.refresh_field("items");
					me.update_manual_distribution();
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

	calculate_taxes_and_totals: function() {
		var total = 0.0;

		$.each(this.frm.doc.taxes || [], function(i, d) {
			d.amount = flt(d.amount, precision("amount", d));
			total += flt(d.amount);
		});

		var total_allocated_amount = frappe.utils.sum($.map(this.frm.doc["advances"] || [], function(adv) {
			return flt(adv.allocated_amount, precision("allocated_amount", adv));
		}));

		this.frm.set_value("grand_total", flt(total, precision("grand_total")));
		this.frm.set_value("total_advance", flt(total_allocated_amount, "total_advance"));
		this.frm.set_value("outstanding_amount", flt(total - total_allocated_amount, "outstanding_amount"));
	},

	set_applicable_charges_for_item: function() {
		var me = this;
		if(me.frm.doc.items.length) {
			var totals = {
				'amount': 0.0,
				'qty': 0.0,
				'weight': 0.0
			};
			$.each(me.frm.doc.items || [], function(i, item) {
				totals.amount += flt(item.amount);
				totals.qty += flt(item.qty);
				totals.weight += flt(item.weight);
			});

			var charges_map = [];
			var manual_account_heads = new Set;
			var idx = 0;
			$.each(me.frm.doc.taxes || [], function(i, tax) {
				var based_on = tax.distribution_criteria.toLowerCase();

				if (based_on == "manual") {
					manual_account_heads.add(tax.account_head);
				} else {
					if(!totals[based_on]) {
						frappe.throw(__("Cannot distribute by {0} because total {1} is 0", [based_on, based_on]));
					}

					charges_map[idx] = [];
					$.each(me.frm.doc.items || [], function(iItem, item) {
						charges_map[idx][iItem] = flt(tax.amount) * flt(item[based_on]) / flt(totals[based_on]);
						if(!item[based_on])
							frappe.msgprint(__("Item #{0} has 0 {1}", [item.idx, based_on]))
					});
					++idx;
				}
			});

			if(manual_account_heads.size)
				me.validate_manual_distribution_totals();

			var accumulated_taxes = 0.0;
			$.each(me.frm.doc.items || [], function(iItem, item) {
				var item_total_tax = 0.0;
				for (var i = 0; i < charges_map.length; ++i) {
					item_total_tax += charges_map[i][iItem];
				}

				Object.keys(item.manual_distribution_data).forEach(function(account_head) {
					if(manual_account_heads.has(account_head)) {
						item_total_tax += flt(item.manual_distribution_data[account_head]);
					}
				});

				item.applicable_charges = flt(item_total_tax, precision("applicable_charges", item));
				accumulated_taxes += item.applicable_charges;
			});

			/*if (accumulated_taxes != me.frm.doc.grand_total) {
				var diff = me.frm.doc.grand_total - flt(accumulated_taxes);
				me.frm.doc.items.slice(-1)[0].applicable_charges += diff;
			}*/

			refresh_field("items");
		}
	},

	validate_manual_distribution_totals: function() {
		var me = this;
		var tax_account_totals = {};
		var item_totals = {};

		$.each(me.frm.doc.taxes || [], function(i, tax) {
			if(tax.distribution_criteria == "Manual" && tax.account_head) {
				if(!tax_account_totals.hasOwnProperty(tax.account_head)) {
					tax_account_totals[tax.account_head] = 0.0;
					item_totals[tax.account_head] = 0.0;
				}
				tax_account_totals[tax.account_head] += flt(tax.amount);
			}
		});

		$.each(me.frm.doc.items || [], function(i, item) {
			if(item.item_code) {
				Object.keys(item.manual_distribution_data).forEach(function(account_head) {
					if(item_totals.hasOwnProperty(account_head)) {
						item_totals[account_head] += flt(item.manual_distribution_data[account_head]);
					}
				});
			}
		});
		Object.keys(tax_account_totals).forEach(function(account_head) {
			var currency = erpnext.get_currency(me.frm.doc.company);
			var digits = precision("grand_total");
			var diff = flt(tax_account_totals[account_head]) - flt(item_totals[account_head]);
			diff = flt(diff, digits);

			if(Math.abs(diff) < (2.0 / (10**digits))) {
				var last = me.frm.doc.items.length - 1;
				me.frm.doc.items[last].manual_distribution_data[account_head] += diff;
				me.update_item_manual_distribution_json(last);
			}
			else {
				frappe.msgprint(__("Tax amount for {} ({}) does not match the total in the manual distribution table ({})",
					[account_head, format_currency(tax_account_totals[account_head], currency, precision), format_currency(item_totals[account_head], currency, precision)]));
				frappe.validated = false;
			}
		});
	},

	distribution_criteria: function() {
		this.update_manual_distribution();
	},
	account_head: function() {
		this.update_manual_distribution();
	},
	taxes_add: function() {
		this.update_manual_distribution();
	},
	taxes_remove: function() {
		this.update_manual_distribution();
	},
	taxes_move: function() {
		this.update_manual_distribution();
	},
	items_add: function() {
		this.update_manual_distribution();
	},
	items_remove: function() {
		this.update_manual_distribution();
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
			});
		}
	},

	party: function() {
		var me = this;
		if(me.frm.doc.party && me.frm.doc.company) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: me.frm.doc.company,
					party_type: me.frm.doc.party_type,
					party: me.frm.doc.party
				},
				callback: function(r) {
					if(!r.exc && r.message) {
						me.frm.set_value("credit_to", r.message);
					}
				}
			});
		}
	},
});

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);