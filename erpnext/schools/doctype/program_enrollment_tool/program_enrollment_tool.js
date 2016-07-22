// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
cur_frm.add_fetch("student", "title", "student_name");
cur_frm.add_fetch("student_applicant", "title", "student_name");

frappe.ui.form.on("Program Enrollment Tool", {
	"refresh": function(frm) {
		frm.disable_save();
	},
	
	"get_students": function(frm) {
		frm.set_value("students",[]);
		frappe.call({
			method: "get_students",
			doc:frm.doc,
			callback: function(r) {
				if(r.message) {
					frm.set_value("students", r.message);
				}
			}
		})
	},
	
	"enroll_students": function(frm) {
		frappe.call({
			method: "enroll_students",
			doc:frm.doc,
			callback: function(r) {
					frm.set_value("students", []);
			}
		})
	}
});
