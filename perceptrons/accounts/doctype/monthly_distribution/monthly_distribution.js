// Copyright (c) 2015, Hash Include Solutions FZC and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Monthly Distribution", {
	onload(frm) {
		if (frm.doc.__islocal) {
			return frm.call("get_months").then(() => {
				frm.refresh_field("percentages");
			});
		}
	},

	refresh(frm) {
		frm.toggle_display("distribution_id", frm.doc.__islocal);
	},
});
