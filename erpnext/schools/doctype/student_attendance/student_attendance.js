// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("course_schedule", "schedule_date", "date");
cur_frm.add_fetch("course_schedule", "student_batch", "student_batch");

frappe.ui.form.on('Student Attendance', {
	onload: function(frm){
		cur_frm.set_query("student_batch", function(){
			return{
				"filters": {
					"active": 1
				}
			};
		});
	}
});
