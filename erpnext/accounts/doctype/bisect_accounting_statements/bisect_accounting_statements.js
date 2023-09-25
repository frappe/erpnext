// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bisect Accounting Statements", {
	refresh(frm) {
		frm.add_custom_button(__('Bisect Left'), () =>
			frm.trigger("bisect_left")
		);

		frm.add_custom_button(__('Bisect Right'), () =>
			frm.trigger("bisect_right")
		);

		frm.add_custom_button(__('Up'), () =>
			frm.trigger("move_up")
		);
		frm.add_custom_button(__('Bisect'), () =>
			frm.trigger("bisect")
		);
		// frm.change_custom_button_type(__('Bisect'), null, 'primary');
	},
	bisect(frm) {
		frm.call({
			doc: frm.doc,
			method: 'bisect',
			callback: (r) => {
				console.log(r);
			}
		});
	}
});
