cur_frm.add_fetch("employee", "department", "department");
cur_frm.add_fetch("employee", "image", "image");

frappe.ui.form.on("Instructor", "refresh", function(frm) {
	if(!frm.doc.__islocal) {
		frm.add_custom_button(__("Course Schedule"), function() {
			frappe.route_options = {
				instructor: frm.doc.name
			}
			frappe.set_route("List", "Course Schedule");
		});
	}
});
