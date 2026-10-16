// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cheque", {
	// The server refuses a cancel without a reason, so ask for one and cancel through
	// cancel_with_reason instead of the standard cancel.
	async before_cancel(frm) {
		const { reason, remarks } = await ask_reason(frm);
		frappe.validated = false;
		try {
			await frm.call("cancel_with_reason", { reason, remarks });
			await frm.reload_doc();
		} catch {
			// the server message already explains the failure
		}
	},
});

function ask_reason(frm) {
	return new Promise((resolve, reject) => {
		let answered = false;
		const dialog = new frappe.ui.Dialog({
			title: __("Cancel Cheque {0}", [frm.doc.cheque_no]),
			// the reason list would otherwise open by itself, as the first input
			no_focus: true,
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Autocomplete",
					label: __("Cancellation Reason"),
					options: frappe.meta.get_docfield("Cheque", "cancellation_reason").options,
					reqd: 1,
				},
				{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") },
			],
			primary_action_label: __("Cancel Cheque"),
			primary_action(values) {
				answered = true;
				dialog.hide();
				resolve(values);
			},
		});
		dialog.onhide = () => answered || reject();
		dialog.show();
	});
}
