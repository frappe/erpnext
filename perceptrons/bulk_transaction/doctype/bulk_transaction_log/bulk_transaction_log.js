// Copyright (c) 2023, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Transaction Log", {
	refresh(frm) {
		frm.add_custom_button(
			__("Succeeded Entries"),
			function () {
				frappe.set_route("List", "Bulk Transaction Log Detail", {
					date: frm.doc.date,
					transaction_status: "Success",
				});
			},
			__("View")
		);
		frm.add_custom_button(
			__("Failed Entries"),
			function () {
				frappe.set_route("List", "Bulk Transaction Log Detail", {
					date: frm.doc.date,
					transaction_status: "Failed",
				});
			},
			__("View")
		);
		if (frm.doc.failed) {
			frm.add_custom_button(__("Retry Failed Transactions"), function () {
				frappe.call({
					method: "perceptrons.utilities.bulk_transaction.retry",
					args: { date: frm.doc.date },
				});
			});
		}
	},
});
