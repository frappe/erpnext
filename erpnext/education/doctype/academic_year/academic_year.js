frappe.ui.form.on("Academic Year", "refresh", function(frm) {
	if(!frm.doc.__islocal) {
		frm.add_custom_button(__("Student Group"), function() {
			frappe.route_options = {
				academic_year: frm.doc.name
			}
			frappe.set_route("List", "Student Group");
		});
	}
});