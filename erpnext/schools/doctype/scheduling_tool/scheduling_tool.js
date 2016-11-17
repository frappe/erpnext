cur_frm.add_fetch("student_group", "program", "program");
cur_frm.add_fetch("student_group", "student_batch", "student_batch");
cur_frm.add_fetch("student_group", "course", "course");
cur_frm.add_fetch("student_group", "academic_year", "academic_year");
cur_frm.add_fetch("student_group", "academic_term", "academic_term");

frappe.ui.form.on("Scheduling Tool", "refresh", function(frm) {
	frm.disable_save();
	frm.page.set_primary_action(__("Schedule Course"), function() {
		frappe.call({
			method: "schedule_course",
			doc:frm.doc
		})
	});
});