frappe.ui.form.on("Newsletter List", "refresh", function(frm) {
	if(!frm.is_new()) {
		frm.add_custom_button(__("View Subscribers"), function() {
			frappe.route_options = {"newsletter_list": frm.doc.name};
			frappe.set_route("Report", "Newsletter List Subscriber");
		});

		frm.add_custom_button(__("Import Subscribers"), function() {
			frappe.prompt({fieldtype:"Select", options: frm.doc.__onload.import_types,
				label:__("Import Email From"), fieldname:"doctype", reqd:1}, function(data) {
					frappe.call({
						method: "erpnext.crm.doctype.newsletter_list.newsletter_list.import_from",
						args: {
							"name": frm.doc.name,
							"doctype": data.doctype
						},
						callback: function(r) {
							frm.set_value("total_subscribers", r.message);
						}
					})
				}, __("Import Subscribers"), __("Import"));
		});

		frm.add_custom_button(__("New Newsletter"), function() {
			frappe.route_options = {"newsletter_list": frm.doc.name};
			new_doc("Newsletter");
		});

	}
});
