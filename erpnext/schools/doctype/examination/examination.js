cur_frm.add_fetch("student_group", "course", "course");
cur_frm.add_fetch("examiner", "instructor_name", "examiner_name");
cur_frm.add_fetch("supervisor", "instructor_name", "supervisor_name");
cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Examination" ,{
	student_group : function(frm) {
		frm.set_value("results" ,"");
		if (frm.doc.student_group) {
			frappe.call({
				method: "erpnext.schools.api.get_student_group_students",
				args: {
					"student_group": frm.doc.student_group
				},
				callback: function(r) {
					if (r.message) {
						$.each(r.message, function(i, d) {
							var row = frappe.model.add_child(cur_frm.doc, "Examination Result", "results");
							row.student = d.student;
							row.student_name = d.student_name;
						});
					}
					refresh_field("results");
				}
			});
		}
	}
});