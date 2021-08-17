// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shopify Log', {
	refresh: function(frm) {
		if (frm.doc.request_data && frm.doc.status=='Error'){
			frm.add_custom_button('Resync', function() {
				frappe.call({
					method:"erpnext.erpnext_integrations.doctype.shopify_log.shopify_log.resync",
					args:{
						method:frm.doc.method,
						name: frm.doc.name,
						request_data: frm.doc.request_data
					},
					callback: function(r){
						frappe.msgprint(__("Order rescheduled for sync"))
					}
				})
			}).addClass('btn-primary');
		}

	let app_link = "<a href='https://frappecloud.com/marketplace/apps/ecommerce-integrations' target='_blank'>Ecommerce Integrations</a>"
	frm.dashboard.add_comment(__("Shopify Integration will be removed from ERPNext in Version 14. Please install {0} app to continue using it.", [app_link]), "yellow", true);
	}
});
