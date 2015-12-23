frappe.ui.form.on("Hub Settings", "onload", function(frm) {
	if(!frm.doc.seller_country) {
		frm.set_value("seller_country", frappe.defaults.get_default("Country"));
	}
	if(!frm.doc.seller_name) {
		frm.set_value("seller_name", frappe.defaults.get_default("Company"));
	}
});

frappe.ui.form.on("Hub Settings", "refresh", function(frm) {
	// make mandatory if published
	frm.toggle_reqd(["seller_name", "seller_email", "seller_country"], frm.doc.publish);
});

frappe.ui.form.on("Hub Settings", "publish", function(frm) {
	frm.trigger("refresh");
});
