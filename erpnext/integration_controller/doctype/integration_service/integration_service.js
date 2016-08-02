// Copyright (c) 2016, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Integration Service', {
	onload: function(frm) {
		frappe.call({
			method: "erpnext.integration_controller.doctype.integration_service.integration_service.get_integration_services",
			callback: function(r){
				set_field_options("service", r.message)
			}
		})
	},
	service: function(frm) {
		frm.events.load_service_config(frm)
	},
	load_service_config: function(frm) {
		$c('runserverobj',args={'method':'set_service_config', 'docs': frm.doc}, function(r, rt){
			frm.refresh_field("authentication_details");
			frm.refresh_field("service_events");
		});
	}
});
