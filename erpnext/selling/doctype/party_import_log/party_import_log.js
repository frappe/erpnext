// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Party Import Log", {
	refresh(frm) {
		// Primary affordance — jump into the wizard
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Wizard"), () => {
				frappe.set_route("party-import-wizard", frm.doc.name);
			}).addClass("btn-primary");
		}

		// Status indicator
		const status_color_map = {
			Draft: "grey",
			Mapping: "blue",
			Resolving: "blue",
			Reviewing: "blue",
			Importing: "orange",
			Completed: "green",
			Failed: "red",
			Cancelled: "grey",
		};
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, status_color_map[frm.doc.status] || "grey");
		}
	},
});
