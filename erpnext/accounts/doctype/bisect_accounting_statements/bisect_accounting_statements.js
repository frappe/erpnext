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
		frm.add_custom_button(__('Build Tree'), () =>
			frm.trigger("build_tree")
		);
	},
	bisect_left(frm) {
		frm.call({
			doc: frm.doc,
			method: 'bisect_left',
			callback: (r) => {
				console.log(r);
			}
		});
	},
	bisect_right(frm) {
		frm.call({
			doc: frm.doc,
			method: 'bisect_right',
			callback: (r) => {
				console.log(r);
			}
		});
	},
	move_up(frm) {
		frm.call({
			doc: frm.doc,
			method: 'move_up',
			callback: (r) => {
				console.log(r);
			}
		});
	},
	build_tree(frm) {
		frm.call({
			doc: frm.doc,
			method: 'build_tree',
			callback: (r) => {
				console.log(r);
			}
		});
	},
});
