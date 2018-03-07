// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Woocommerce Settings', {
	refresh (frm) {
		frm.trigger("add_button_generate_secret");
		//frm.trigger("add_button_force_delete");
		//frm.trigger("add_button_install_webhooks");
		frm.trigger("check_enabled");
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
					}).done(r=>frm.reload_doc())
					.fail(r=>frappe.msgprint(__("Could not generate Secret")));
				}
			)
		});
	},

	// add_button_force_delete (frm) {
	// 	frm.add_custom_button(__('Force Delete'), () => {
	// 		frappe.confirm(
	// 			__("This will clear all your Woocommerce Data, are you sure?"),
	// 			() => {
	// 				frappe.call({
	// 					type:"POST",
	// 					method:"erpnext.erpnext_integrations.doctype.woocommerce_settings.woocommerce_settings.force_delete",
	// 				}).done(r=>frm.reload_doc())
	// 				.fail(r=>frappe.msgprint(__("Could not Delete Woocommerce Data")));
	// 			}
	// 		)
	// 	});
	// },

	// add_button_install_webhooks (frm) {
	// 	if (frm.doc.enable_sync &&
	// 		frm.doc.woocommerce_server_url != null &&
	// 		frm.doc.api_consumer_key != null &&
	// 		frm.doc.api_consumer_secret != null &&
	// 		frm.doc.secret != null) {
	// 		frm.add_custom_button(__('Install'), () => {
	// 			frappe.confirm(
	// 				__("This will create Webhooks on Woocommerce Server"),
	// 				() => {
	// 					frappe.call({
	// 						type:"POST",
	// 						doc: frm.doc,
	// 						method:"create_webhooks",
	// 						freeze:true,
	// 					}).done(r=>frm.reload_doc())
	// 					.fail(r=>frappe.msgprint(__("Could not create Webhooks on Woocommerce")));
	// 				}
	// 			)
	// 		});
	// 	}
	// },

	check_enabled (frm) {
		frm.set_df_property("woocommerce_server_url", "reqd", frm.doc.enable_sync);
		frm.set_df_property("api_consumer_key", "reqd", frm.doc.enable_sync);
		frm.set_df_property("api_consumer_secret", "reqd", frm.doc.enable_sync);
	}
});
