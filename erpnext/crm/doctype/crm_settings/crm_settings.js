// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("CRM Settings", {
	refresh: function (frm) {
		const flag = frm.events.calculate_visiblity_flag(frm);

		frm.set_df_property("allowed_users", "hidden", !flag);
		frm.set_df_property("allowed_users", "reqd", flag);
	},

	enable_frappe_crm_data_synchronization: function (frm) {
		const flag = frm.events.calculate_visiblity_flag(frm);

		if (flag) {
			frappe.show_alert(
				__("Allowed Users is required for data synchronization from remote Frappe CRM site.")
			);
		}

		/*
		make allowed_users field visible and mandatory if enable_frappe_crm_data_synchronization
		is set and crm app is not installed.
		*/

		frm.set_df_property("allowed_users", "hidden", !flag);
		frm.set_df_property("allowed_users", "reqd", flag);
	},

	calculate_visiblity_flag: function (frm) {
		const crm_sync_enabled = frm.doc.enable_frappe_crm_data_synchronization;
		const is_crm_installed = cint(frappe.utils.get_installed_apps().includes("crm"));

		return crm_sync_enabled && !is_crm_installed;
	},
});
