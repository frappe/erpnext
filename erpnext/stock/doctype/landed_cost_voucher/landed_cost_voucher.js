// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.provide("erpnext.stock");

erpnext.stock.LandedCostVoucher = erpnext.stock.StockController.extend({
	setup: function() {
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

		this.frm.add_fetch("receipt_document", "supplier", "supplier");
		this.frm.add_fetch("receipt_document", "posting_date", "posting_date");
		this.frm.add_fetch("receipt_document", "base_grand_total", "grand_total");
		this.frm.add_fetch("company", "cost_center", "cost_center");
	},

	refresh: function(doc) {
		this.show_general_ledger();

		if (doc.docstatus===1 && doc.outstanding_amount != 0 && frappe.model.can_create("Payment Entry")) {
			var me = this;
			this.frm.add_custom_button(__('Payment'),
				function() { me.make_payment_entry(me.frm) }, __("Make"));
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

	make_payment_entry: function(frm) {
		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		return frappe.call({
			method: method,
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
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
				method: "get_items_from_purchase_receipts",
				callback: function(r, rt) {
					me.set_applicable_charges_for_item();
				}
			});
		}
	},

	amount: function(frm) {
		this.set_total_taxes_and_charges();
		this.set_applicable_charges_for_item();
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

		if(this.frm.doc.taxes.length) {
			
			var total_item_cost = 0.0;
			var based_on = this.frm.doc.distribute_charges_based_on.toLowerCase();
			$.each(this.frm.doc.items || [], function(i, d) {
				total_item_cost += flt(d[based_on])
			});

			var total_charges = 0.0;
			$.each(this.frm.doc.items || [], function(i, item) {
				item.applicable_charges = flt(item[based_on]) * flt(me.frm.doc.total_taxes_and_charges) / flt(total_item_cost)			
				item.applicable_charges = flt(item.applicable_charges, precision("applicable_charges", item))
				total_charges += item.applicable_charges
			});

			if (total_charges != this.frm.doc.total_taxes_and_charges){
				var diff = this.frm.doc.total_taxes_and_charges - flt(total_charges)
				this.frm.doc.items.slice(-1)[0].applicable_charges += diff
			}
			refresh_field("items");
		}
	},
	distribute_charges_based_on: function (frm) {
		this.set_applicable_charges_for_item();
	},

	supplier: function() {
		var me = this;
		if(me.frm.doc.company) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: me.frm.doc.company,
					party_type: "Supplier",
					party: me.frm.doc.supplier
				},
				callback: function(r) {
					if(!r.exc && r.message) {
						me.frm.set_value("payable_account", r.message);
					}
				}
			});
		}
	},
});

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);

cur_frm.fields_dict["cost_center"].get_query = function() {
	return {
		filters: {
			"company": frm.doc.company
		}
	};
};

cur_frm.fields_dict["payable_account"].get_query = function() {
	return {
		filters: {
			'account_type': 'Payable',
			'is_group': 0,
			'company': doc.company
		}
	};
};