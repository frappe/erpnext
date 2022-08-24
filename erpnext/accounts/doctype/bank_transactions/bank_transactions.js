// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transactions', {
	// refresh: function(frm) {

	// }
	check: function (frm) {
		frappe.call({
			method: "verified_check",
			doc: frm.doc,
		});
	},

	debit_note: function (frm) {
		frappe.call({
			method: "verified_check2",
			doc: frm.doc,
		});
	},

	credit_note: function (frm) {
		frappe.call({
			method: "verified_check3",
			doc: frm.doc,
		});
	},

	bank_deposit: function (frm) {
		frappe.call({
			method: "verified_check4",
			doc: frm.doc,
		});
	},

	refresh: function (frm) {
		frm.events.make_custom_buttons(frm);
	},

	make_custom_buttons: function (frm) {
		if (frm.doc.docstatus == 3) {
			frm.add_custom_button(__("Pre-reconciled"),
				() => frm.events.prereconciled(frm), __('Create'));

			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
		if (frm.doc.docstatus == 4) {
			frm.add_custom_button(__("Return Transit"),
				() => frm.events.transit(frm), __('Create'));

			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},

	prereconciled: function (frm) {
		frappe.call({
			method: "prereconciled",
			doc: frm.doc,
		});
	},

	transit: function (frm) {
		frappe.call({
			method: "transit",
			doc: frm.doc,
		});
	},

});
