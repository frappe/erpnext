// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Woocommerce Settings', {
	refresh (frm) {
		frm.trigger("add_button_generate_secret");
		frm.trigger("check_enabled");
		frm.set_query("tax_account", ()=>{
			return {
				"filters": {
					"company": frappe.defaults.get_default("company"),
					"is_group": 0
				}
			};
		});
	},

	enable_sync (frm) {
		frm.trigger("check_enabled");
	},

	add_button_generate_secret(frm) {
		frm.add_custom_button(__('Generate Secret'), () => {
			frappe.confirm(
				__("Apps using current key won't be able to access, are you sure?"),
				() => {
					frappe.call({
						type:"POST",
						method:"erpnext.erpnext_integrations.doctype.woocommerce_settings.woocommerce_settings.generate_secret",
					}).done(() => {
						frm.reload_doc();
					}).fail(() => {
						frappe.msgprint(__("Could not generate Secret"));
					});
				}
			);
		});
	},

	check_enabled (frm) {
		frm.set_df_property("woocommerce_server_url", "reqd", frm.doc.enable_sync);
		frm.set_df_property("api_consumer_key", "reqd", frm.doc.enable_sync);
		frm.set_df_property("api_consumer_secret", "reqd", frm.doc.enable_sync);
	}
});