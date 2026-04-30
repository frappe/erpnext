// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process Period Closing Voucher", {
	refresh(frm) {
		if (frm.doc.docstatus == 1 && ["Queued"].find((x) => x == frm.doc.status)) {
			let execute_btn = __("Start");

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: "erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.start_pcv_processing",
					args: {
						docname: frm.doc.name,
					},
				}).then((r) => {
					if (!r.exc) {
						frappe.show_alert(__("Job Started"));
						frm.reload_doc();
					}
				});
			});
		}

		if (frm.doc.docstatus == 1 && ["Running"].find((x) => x == frm.doc.status)) {
			let execute_btn = __("Pause");

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: "erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.pause_pcv_processing",
					args: {
						docname: frm.doc.name,
					},
				}).then((r) => {
					if (!r.exc) {
						frappe.show_alert(__("PCV Paused"));
						frm.reload_doc();
					}
				});
			});
		}

		if (frm.doc.docstatus == 1 && ["Paused"].find((x) => x == frm.doc.status)) {
			let execute_btn = __("Resume");

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: "erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.resume_pcv_processing",
					args: {
						docname: frm.doc.name,
					},
				}).then((r) => {
					if (!r.exc) {
						frappe.show_alert(__("PCV Resumed"));
						frm.reload_doc();
					}
				});
			});
		}
		// progress bar
		let progress = 0;

		let normal_finished = frm.doc.normal_balances.filter((x) => x.status == "Completed").length;
		let opening_finished = frm.doc.z_opening_balances.filter((x) => x.status == "Completed").length;

		progress =
			((normal_finished + opening_finished) /
				(frm.doc.normal_balances.length + frm.doc.z_opening_balances.length)) *
			100;
		frm.dashboard.add_progress("Books closure progress", progress, "");
	},
});
