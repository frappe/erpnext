// Copyright (c) 2016, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Ledger Entry", {
	refresh: function (frm) {
		frm.page.btn_secondary.hide();
	},
});
