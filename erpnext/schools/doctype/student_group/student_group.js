	cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Student Group", {
	onload: function(frm) {
		frm.set_query("academic_term", function() {
			return {
				"filters": {
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
	},

	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Course Schedule"), function() {
				frappe.set_route("List", "Course Schedule");
			});

			frm.add_custom_button(__("Assessment Plan"), function() {
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
				frappe.set_route("List", "Newsletter");
			});
		}
	},
	
	group_based_on: function(frm) {
		if (frm.doc.group_based_on == "Batch") {
			frm.doc.course = null;
		}
		else if (frm.doc.group_based_on == "Course") {
			frm.doc.program = null;
			frm.doc.batch = null;
		}
		else if (frm.doc.group_based_on == "Activity") {
			frm.doc.program =null;
			frm.doc.batch =null;
			frm.doc.CourseQ =null;
		}
		frm.trigger("set_name");
	},

	set_name: function(frm) {
		var name;
		if (frm.doc.group_based_on == "Course") {
			name = "Course-" + frm.doc.course + "-" + (frm.doc.academic_term?frm.doc.academic_term:frm.doc.academic_year);
		} else if (frm.doc.group_based_on == "Batch") {
			name = "Batch-" + frm.doc.program + "-" + frm.doc.batch + "-"
				+ (frm.doc.academic_term?frm.doc.academic_term:frm.doc.academic_year); 
		} else if (frm.doc.group_based_on == "Activity") {
			name = "Activity" + "-" + (frm.doc.academic_term?frm.doc.academic_term:frm.doc.academic_year);
		}
		frm.set_value("student_group_name", name);
	},

	program:function(frm) {
		frm.trigger("set_name");
	},

	batch:function(frm) {
		frm.trigger("set_name");
	},

	course:function(frm) {
		frm.trigger("set_name");
	},

	get_students: function(frm) {
		if (frm.doc.group_based_on != "Activity") {
			var student_list = [];
			var max_roll_no = 0;
			$.each(frm.doc.students, function(i,d) {
				student_list.push(d.student);
				if (d.group_roll_number>max_roll_no) {
					max_roll_no = d.group_roll_number;
				}
			});
			frappe.call({
				method: "erpnext.schools.doctype.student_group.student_group.get_students",
				args: {
					"academic_year": frm.doc.academic_year,
					"group_based_on": frm.doc.group_based_on,
					"program": frm.doc.program,
					"batch" : frm.doc.batch,
					"course": frm.doc.course	
				},
				callback: function(r) {
					if(r.message) {
						$.each(r.message, function(i, d) {
							if(!in_list(student_list, d.student)) {
								var s = frm.add_child("students");
								s.student = d.student;
								s.student_name = d.student_name;
								if (d.active === 0) {
									s.active = 0;
								}
								s.group_roll_number = ++max_roll_no;
							}
						});
						refresh_field("students");
						frm.save();
					} else {
						frappe.msgprint(__("Student Group is already updated."))
					}
				}
			})	
		} else {
			frappe.msgprint(__("Select students manually for the Activity based Group"));
		}
	}

});