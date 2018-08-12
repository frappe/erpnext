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
				var d = locals[cdt][cdn]

				var filters = [
					[d.receipt_document_type, 'docstatus', '=', '1'],
					[d.receipt_document_type, 'company', '=', me.frm.doc.company],
				]

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
			var account_type = ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation"];
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

	refresh: function(doc) {
		this.show_general_ledger();

		if (doc.docstatus===1 && doc.outstanding_amount != 0 && frappe.model.can_create("Payment Entry")) {
			cur_frm.add_custom_button(__('Payment'), this.make_payment_entry, __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
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
			return this.frm.call({
				doc: me.frm.doc,
				method: "get_items_from_purchase_receipts"
			});
		}
	},

	distribute_applicable_charges: function(frm) {
		this.set_total_taxes_and_charges();
		this.set_applicable_charges_for_item();
	},

	amount: function(frm) {
		this.set_total_taxes_and_charges();
	},

	set_total_taxes_and_charges: function() {
		var total_taxes_and_charges = 0.0;
		$.each(this.frm.doc.taxes || [], function(i, d) {
			total_taxes_and_charges += flt(d.amount)
		});
		cur_frm.set_value("total_taxes_and_charges", total_taxes_and_charges);
		cur_frm.set_value("outstanding_amount", total_taxes_and_charges);
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
			$.each(me.frm.doc.taxes || [], function(iTax, tax) {
				charges_map[iTax] = [];
				var based_on = tax.distribution_criteria.toLowerCase();

				if (!totals[based_on])
					frappe.throw(__("Cannot distribute by {0} because total {1} is 0", [based_on, based_on]));

				$.each(me.frm.doc.items || [], function(iItem, item) {
					charges_map[iTax][iItem] = flt(tax.amount) * flt(item[based_on]) / flt(totals[based_on]);
					if (!item[based_on])
						frappe.msgprint(__("Item #{0} has 0 {1}", [iItem+1, based_on]))
				});
			});

			var accumulated_taxes = 0.0;
			$.each(me.frm.doc.items || [], function(iItem, item) {
				var item_total_tax = 0.0;
				for (var iTax = 0; iTax < me.frm.doc.taxes.length; ++iTax) {
					item_total_tax += charges_map[iTax][iItem];
				}

				item.applicable_charges = flt(item_total_tax, precision("applicable_charges", item));
				accumulated_taxes += item.applicable_charges;
			});

			if (accumulated_taxes != me.frm.doc.total_taxes_and_charges) {
				var diff = me.frm.doc.total_taxes_and_charges - flt(accumulated_taxes);
				me.frm.doc.items.slice(-1)[0].applicable_charges += diff;
			}

			refresh_field("items");
		}
	},

	supplier: function() {
		var me = this;
		if(me.frm.doc.supplier && me.frm.doc.company) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: me.frm.doc.company,
					party_type: "Supplier",
					party: me.frm.doc.supplier
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