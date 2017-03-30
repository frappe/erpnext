cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Student Group", {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Course Schedule"), function() {
				frappe.route_options = {
					student_group: frm.doc.name
				}
				frappe.set_route("List", "Course Schedule");
			});

			frm.add_custom_button(__("Assessment Plan"), function() {
				frappe.route_options = {
					student_group: frm.doc.name
				}
				frappe.set_route("List", "Assessment Plan");
			});
			frm.add_custom_button(__("Update Email Group"), function() {
				frappe.call({
					method: "erpnext.schools.api.update_email_group",
					args: {
						"doctype": "Student Group",
						"name": frm.doc.name
					}
				});
			});
			frm.add_custom_button(__("Newsletter"), function() {
				frappe.route_options = {
					email_group: frm.doc.name
				}
				frappe.set_route("List", "Newsletter");
			});
		}
	},

	onload: function(frm) {
		frm.set_query("academic_term", function() {
			return {
				"filters": {
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
	}
});

//If Student Batch is entered, deduce program, academic_year and academic term from it
cur_frm.add_fetch("student_batch", "program", "program");
cur_frm.add_fetch("student_batch", "academic_term", "academic_term");
cur_frm.add_fetch("student_batch", "academic_year", "academic_year");