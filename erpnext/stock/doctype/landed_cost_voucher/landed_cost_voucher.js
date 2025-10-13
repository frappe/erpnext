// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.landed_cost_taxes_and_charges.setup_triggers("Landed Cost Voucher");
erpnext.stock.LandedCostVoucher = class LandedCostVoucher extends erpnext.stock.StockController {
	refresh() {
		var help_content = `<br><br>
			<table class="table table-bordered" style="background-color: var(--scrollbar-track-color);">
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

		if (this.frm.doc.company) {
			let company_currency = frappe.get_doc(":Company", this.frm.doc.company).default_currency;
			this.frm.set_currency_labels(
				["total_taxes_and_charges", "total_vendor_invoices_cost"],
				company_currency
			);
		}
	}

	get_items_from_purchase_receipts() {
		var me = this;
		if (!this.frm.doc.purchase_receipts.length) {
			frappe.msgprint(__("Please enter Purchase Receipt first"));
		} else {
			return this.frm.call({
				doc: me.frm.doc,
				method: "get_items_from_purchase_receipts",
				callback: function (r, rt) {
					me.set_applicable_charges_for_item();
				},
			});
		}
	}

	amount(frm) {
		this.set_total_taxes_and_charges();
		this.set_applicable_charges_for_item();
	}

	set_total_taxes_and_charges() {
		var total_taxes_and_charges = 0.0;
		$.each(this.frm.doc.taxes || [], function (i, d) {
			total_taxes_and_charges += flt(d.base_amount);
		});
		this.frm.set_value("total_taxes_and_charges", total_taxes_and_charges);
	}

	set_applicable_charges_for_item() {
		var me = this;

		if (this.frm.doc.taxes.length) {
			var total_item_cost = 0.0;
			var based_on = this.frm.doc.distribute_charges_based_on.toLowerCase();

			if (based_on != "distribute manually") {
				$.each(this.frm.doc.items || [], function (i, d) {
					total_item_cost += flt(d[based_on]);
				});

				var total_charges = 0.0;
				$.each(this.frm.doc.items || [], function (i, item) {
					item.applicable_charges =
						(flt(item[based_on]) * flt(me.frm.doc.total_taxes_and_charges)) /
						flt(total_item_cost);
					item.applicable_charges = flt(
						item.applicable_charges,
						precision("applicable_charges", item)
					);
					total_charges += item.applicable_charges;
				});

				if (total_charges != this.frm.doc.total_taxes_and_charges) {
					var diff = this.frm.doc.total_taxes_and_charges - flt(total_charges);
					this.frm.doc.items.slice(-1)[0].applicable_charges += diff;
				}
				refresh_field("items");
			}
		}
	}
	distribute_charges_based_on(frm) {
		this.set_applicable_charges_for_item();
	}

	items_remove() {
		this.trigger("set_applicable_charges_for_item");
	}
};

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);

frappe.ui.form.on("Landed Cost Taxes and Charges", {
	expense_account: function (frm, cdt, cdn) {
		frm.events.set_account_currency(frm, cdt, cdn);
	},

	amount: function (frm, cdt, cdn) {
		frm.events.set_base_amount(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Landed Cost Voucher", {
	setup(frm) {
		frm.trigger("setup_queries");
	},

	setup_queries(frm) {
		frm.set_query("receipt_document", "purchase_receipts", (doc, cdt, cdn) => {
			var d = locals[cdt][cdn];
			var filters = [
				[d.receipt_document_type, "docstatus", "=", 1],
				[d.receipt_document_type, "company", "=", frm.doc.company],
			];

			if (d.receipt_document_type === "Purchase Invoice") {
				filters.push(["Purchase Invoice", "update_stock", "=", 1]);
			} else if (d.receipt_document_type === "Stock Entry") {
				filters.push(["Stock Entry", "purpose", "in", ["Manufacture", "Repack"]]);
			}
			return {
				filters: filters,
			};
		});

		frm.set_query("vendor_invoice", "vendor_invoices", (doc, cdt, cdn) => {
			return {
				query: "erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher.get_vendor_invoices",
				filters: {
					company: doc.company,
				},
			};
		});
	},
});

frappe.ui.form.on("Landed Cost Purchase Receipt", {
	receipt_document(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.receipt_document) {
			frappe.call({
				method: "get_receipt_document_details",
				doc: frm.doc,
				args: {
					receipt_document: d.receipt_document,
					receipt_document_type: d.receipt_document_type,
				},
				callback: function (r) {
					if (r.message) {
						$.extend(d, r.message);
						refresh_field("purchase_receipts");
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Landed Cost Vendor Invoice", {
	vendor_invoice(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.vendor_invoice) {
			frappe.call({
				method: "get_vendor_invoice_amount",
				doc: frm.doc,
				args: {
					vendor_invoice: d.vendor_invoice,
				},
				callback: function (r) {
					if (r.message) {
						$.extend(d, r.message);
						refresh_field("vendor_invoices");
					}
				},
			});
		}
	},
});
