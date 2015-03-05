// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Offer Letter", {
	select_terms: function(frm) {
		frappe.model.get_value("Terms and Conditions", frm.doc.select_terms, "terms", function(value) {
			frm.set_value("terms", value.terms);
		});
	}
});
