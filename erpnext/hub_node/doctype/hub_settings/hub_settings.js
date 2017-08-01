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
	on_update: function(frm) {
		if(frm.doc.password) {
			frm.toggle_display("publish", true);
		}
	},
	enabled: function(frm) {
		frm.trigger("toggle_reqd_fields")

		// 	implies registering, mandatory fields, won't let save until profile filled
		// set enabled property on button click, choreograph hiding and unhiding

		// disable
		// unset enabled property on button click, choreograph hiding and unhiding
		// implied by unregister
	},
	toggle_reqd_fields: function(frm) {
		frm.toggle_reqd("hub_user_name", frm.doc.enabled);
		frm.toggle_reqd("country", frm.doc.enabled);
		frm.toggle_reqd("company", frm.doc.enabled);
		frm.toggle_reqd("email", frm.doc.enabled);
	},
	unregister: function(frm) {
		// on click of red unregister button at the bottom
		// clear all fields and uncheck enabled
		// call server side unregister to make call
	},

});