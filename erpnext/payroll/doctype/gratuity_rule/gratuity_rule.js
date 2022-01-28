// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gratuity Rule', {
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on('Gratuity Rule Slab', {

	/*
		Slabs should be in order like

		from | to | fraction
		0    | 4  | 0.5
		4    | 6  | 0.7

		So, on row addition setting current_row.from = previous row.to.
		On to_year insert we have to check that it is not less than from_year

		Wrong order may lead to Wrong Calculation
	*/

	gratuity_rule_slabs_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let array_idx = row.idx - 1;
		if (array_idx > 0) {
			row.from_year = cur_frm.doc.gratuity_rule_slabs[array_idx - 1].to_year;
			frm.refresh();
		}
	},

	to_year(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.to_year <= row.from_year && row.to_year === 0) {
			frappe.throw(__("To(Year) year can not be less than From(year) "));
		}
	}
});
