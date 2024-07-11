// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Bank Transaction"] = {
	onload: function (listview) {
		listview.page.add_inner_button(__('Get Abn Amro Transactions'), function () {
				frappe.call({
					method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction.get_latest_transactions',
					freeze: true,
					freeze_message: __("This may take a few seconds..."),
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint(r.message);
						}
					}
				});
			}
		);listview.page.add_inner_button(__('Get Other Transactions'), function () {
				frappe.call({
					method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction.get_myponto_transactions',
					freeze: true,
					freeze_message: __("This may take a few seconds..."),
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint(r.message);
						}
					}
				});
			}
		);
	},

	add_fields: ["unallocated_amount"],
	get_indicator: function (doc) {
		if (doc.docstatus == 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		} else if (flt(doc.unallocated_amount) <= 0) {
			return [__("Reconciled"), "green", "unallocated_amount,=,0"];
		} else if (flt(doc.unallocated_amount) > 0) {
			return [__("Unreconciled"), "orange", "unallocated_amount,>,0"];
		}
	},
};
