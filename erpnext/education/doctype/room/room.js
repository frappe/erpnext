frappe.ui.form.on("Room", "refresh", function(frm) {
	if(!cur_frm.doc.__islocal) {
		frm.add_custom_button(__("Course Schedule"), function() {
			frappe.route_options = {
				room: frm.doc.name
			}
			frappe.set_route("List", "Course Schedule");
		});
	}
});