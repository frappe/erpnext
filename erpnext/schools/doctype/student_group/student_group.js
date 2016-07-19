cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Student Group", "refresh", function(frm) {
	if(!frm.doc.__islocal) {
		frm.add_custom_button(__("Course Schedule"), function() {
			frappe.route_options = {
				student_group: frm.doc.name
			}
			frappe.set_route("List", "Course Schedule");
		});
		
		frm.add_custom_button(__("Examination"), function() {
			frappe.route_options = {
				student_group: frm.doc.name
			}
			frappe.set_route("List", "Examination");
		});
	}
});