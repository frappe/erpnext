frappe.ui.form.on("Accounts Settings", {
	refresh: function (frm) {
		frm.set_df_property("credit_controller", "label", __("Credit Manager"));
	},
});

frappe.ui.form.on("Company", {
	refresh: function (frm) {
		frm.set_df_property("accounts_frozen_till_date", "label", __("Books Closed Through"));
		frm.set_df_property(
			"role_allowed_for_frozen_entries",
			"label",
			__("Role Allowed to Close Books & Make Changes to Closed Periods")
		);
	},
});
