
frappe.ui.form.on('Accounts Settings', {
	refresh: function(frm) {
		frm.set_df_property("acc_frozen_upto", "label", "Books Closed Through");
		frm.set_df_property("frozen_accounts_modifier", "label", "Role Allowed to Close Books & Make Changes to Closed Periods");
		frm.set_df_property("credit_controller", "label", "Credit Manager");
	}
});
