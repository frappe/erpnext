// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Code', {
	refresh: function(frm) {
			frm.set_df_property("code_table", "hidden", frm.doc.__islocal ? 1:0);
	}
});
