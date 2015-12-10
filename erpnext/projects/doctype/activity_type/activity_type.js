frappe.ui.form.on("Activity Type", {
	refresh: function(frm) {
		frm.add_custom_button(__("Activity Cost per Employee"), function() {
			frappe.route_options = {"activity_type": frm.doc.name};
			frappe.set_route("List", "Activity Cost");
		});
	}
});
