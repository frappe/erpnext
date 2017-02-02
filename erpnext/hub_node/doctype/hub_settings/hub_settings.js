frappe.ui.form.on("Hub Settings", {
	onload: function(frm) {
		if(!frm.doc.country) {
			frm.set_value("country", frappe.defaults.get_default("Country"));
		}
		if(!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("Company"));
		}
	},
	refresh: function(frm) {
		frm.trigger("toggle_reqd_fields")
	},
	enabled: function(frm) {
		frm.trigger("toggle_reqd_fields")
	},
	toggle_reqd_fields: function(frm) {
		frm.toggle_reqd("hub_user_name", frm.doc.enabled);
		frm.toggle_reqd("country", frm.doc.enabled);
		frm.toggle_reqd("company", frm.doc.enabled);
		frm.toggle_reqd("email", frm.doc.enabled);
	}
});