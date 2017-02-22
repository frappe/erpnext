// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("schools")

frappe.ui.form.on('Student Attendance Tool', {
	refresh: function(frm) {
		frm.disable_save();
	},

	based_on: function(frm) {
		if (frm.doc.based_on == "Student Batch") {
			frm.set_value("course_schedule", "");
		} else {
			frm.set_value("student_batch", "");
		}
	},

	student_batch: function(frm) {
		if ((frm.doc.student_batch && frm.doc.date) || frm.doc.course_schedule) {
			var method = "erpnext.schools.doctype.student_attendance_tool.student_attendance_tool.get_student_attendance_records";

			frappe.call({
				method: method,
				args: {
					based_on: frm.doc.based_on,
					student_batch: frm.doc.student_batch,
					date: frm.doc.date,
					course_schedule: frm.doc.course_schedule
				},
				callback: function(r) {
					frm.events.get_students(frm, r.message);
				}
			})
		}
	},

	date: function(frm) {
		frm.trigger("student_batch");
	},

	course_schedule: function(frm) {
		frm.trigger("student_batch");
	},

	get_students: function(frm, students) {
		if (!frm.students_area) {
			frm.students_area = $('<div>')
				.appendTo(frm.fields_dict.students_html.wrapper);
		}
		frm.students_editor = new schools.StudentsEditor(frm, frm.students_area, students)
	}
});


schools.StudentsEditor = Class.extend({
	init: function(frm, wrapper, students) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.make(frm, students);
	},
	make: function(frm, students) {
		var me = this;

		$(this.wrapper).empty();
		var student_toolbar = $('<p>\
			<button class="btn btn-default btn-add btn-xs" style="margin-right: 5px;"></button>\
			<button class="btn btn-xs btn-default btn-remove" style="margin-right: 5px;"></button>\
			<button class="btn btn-default btn-primary btn-mark-att btn-xs"></button></p>').appendTo($(this.wrapper));

		student_toolbar.find(".btn-add")
			.html(__('Check all'))
			.on("click", function() {
				$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if (!$(check).prop("disabled")) {
						check.checked = true;
					}
				});
			});

		student_toolbar.find(".btn-remove")
			.html(__('Uncheck all'))
			.on("click", function() {
				$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if (!$(check).prop("disabled")) {
						check.checked = false;
					}
				});
			});

		var get_present_student = function(student) {
			return students.filter(function(s) {
				return s.idx === idx;
			})
		}
		var get_absent_student = function(idx) {
			return students.filter(function(s) {
				return s.idx === idx;
			})
		}

		student_toolbar.find(".btn-mark-att")
			.html(__('Mark Attendence'))
			.on("click", function() {
				var studs = [];
				$(me.wrapper.find('input[type="checkbox"]')).each(function(i, check) {
					var $check = $(check);
					studs.push({
						student: $check.data().student,
						student_name: $check.data().studentName,
						idx: $check.data().idx,
						disabled: $check.prop("disabled"),
						checked: $check.is(":checked")
					});
				});

				var students_present = studs.filter(function(stud) {
					return !stud.disabled && stud.checked;
				});

				var students_absent = studs.filter(function(stud) {
					return !stud.disabled && !stud.checked;
				});

				frappe.confirm(__("Do you want to update attendance?<br>Present: {0}\
					<br>Absent: {1}", [students_present.length, students_absent.length]), function() {
					frappe.call({
						method: "erpnext.schools.api.mark_attendance",
						args: {
							"students_present": students_present,
							"students_absent": students_absent,
							"student_batch": frm.doc.student_batch,
							"course_schedule": frm.doc.course_schedule,
							"date": frm.doc.date
						},
						callback: function(r) {
							frm.trigger("student_batch");
						}
					});
				});

			});

		var htmls = students.map(function(student) {
			return frappe.render_template("student_button", {
				student: student.student,
				student_name: student.student_name,
				idx: student.idx,
				status: student.status
			})
		});

		$(htmls.join("")).appendTo(me.wrapper);
	}
});