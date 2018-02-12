// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Woocommerce Settings', {
	refresh: function(frm) {

		frm.add_custom_button(__('Generate Secret'), () => {
			frappe.confirm(
				__("Apps using current key won't be able to access, are you sure?"),
				() => {					
					frappe.call({
						type:"POST",
						//method:"agrinext.agrinext.doctype.agrinext_settings.agrinext_settings.generate_guest_key",
						method:"erpnext.erpnext_integrations.doctype.woocommerce_settings.woocommerce_settings.generate_secret",
					}).done(r=>frm.reload_doc())
					.fail(r=>frappe.msgprint(__("Could not generate Secret")));
				}
			)
		});


		frm.add_custom_button(__('Force Delete'), () => {
			frappe.confirm(
				__("This will clear all your Woocommerce Data, are you sure?"),
				() => {					
					frappe.call({
						type:"POST",
						//method:"agrinext.agrinext.doctype.agrinext_settings.agrinext_settings.generate_guest_key",
						method:"erpnext.erpnext_integrations.doctype.woocommerce_settings.woocommerce_settings.force_delete",
					}).done(r=>frm.reload_doc())
					.fail(r=>frappe.msgprint(__("Could not Delete Woocommerce Data")));
				}
			)
		});
		

	}

});
