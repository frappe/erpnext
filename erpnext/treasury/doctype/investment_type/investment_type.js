// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Type", {
	refresh(frm) {
		// named by this field, which Frappe hides once saved; keep it visible, rename via the title
		frm.toggle_display("investment_type", true);
		frm.set_df_property("investment_type", "read_only", frm.is_new() ? 0 : 1);
	},
});
