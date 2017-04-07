frappe.ui.form.on("Course", "refresh", function(frm) {
	if(!cur_frm.doc.__islocal) {
		frm.add_custom_button(__("Program"), function() {
			// frappe.route_options = {
			// 	"Program Course.course": frm.doc.name
			// }
			frappe.set_route("List", "Program");
		});
		
		frm.add_custom_button(__("Student Group"), function() {
			// frappe.route_options = {
			// 	course: frm.doc.name
			// }
			frappe.set_route("List", "Student Group");
		});
		
		frm.add_custom_button(__("Course Schedule"), function() {
			// frappe.route_options = {
			// 	course: frm.doc.name
			// }
			frappe.set_route("List", "Course Schedule");
		});
		
		frm.add_custom_button(__("Assessment Plan"), function() {
			// frappe.route_options = {
			// 	course: frm.doc.name
			// }
			frappe.set_route("List", "Assessment Plan");
		});
	}
});