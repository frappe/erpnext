frappe.provide("schools")

frappe.ui.form.on("Course Schedule" ,{
	onload: function(frm) {
		if (frm.doc.from_datetime && frm.doc.to_datetime) {
			var from_datetime = moment(frm.doc.from_datetime);
			var to_datetime = moment(frm.doc.to_datetime);
			frm.doc.schedule_date = from_datetime.format(moment.defaultFormat);
			frm.doc.from_time = from_datetime.format("HH:mm:ss");
			frm.doc.to_time = to_datetime.format("HH:mm:ss");
		}
		
		cur_frm.set_query("student_batch", function(){
			return{
				"filters": {
					"active": 1
				}
			};
		});
	},
	
	refresh :function(frm) {
		if(!frm.doc.__islocal && frm.doc.student_group) {
			frappe.call({
				method: "erpnext.schools.api.check_attendance_records_exist",
				args: {
					"course_schedule": frm.doc.name
				},
				callback: function(r) {
					if(r.message) {
						hide_field('attendance');
						frm.events.view_attendance(frm)
					}
					else {
						frappe.call({
							method: "erpnext.schools.api.get_student_group_students",
							args: {
								"student_group": frm.doc.student_group
							},
							callback: function(r) {
								if (r.message) {
									frm.events.get_students(frm, r.message)
								}
							}
						});
					}
				}
			});
		}
		else {
			hide_field('attendance');
		}
	},
	
	view_attendance: function(frm) {
		hide_field('attendance');
		frm.add_custom_button(__("View attendance"), function() {
			frappe.route_options = {
				course_schedule: frm.doc.name
			}
			frappe.set_route("List", "Student Attendance");
		});
	},
	
	get_students: function(frm, students) {
		if(!frm.students_area) {
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
				if(!$(check).is(":checked")) {
					check.checked = true;
				}
			});
		});

		student_toolbar.find(".btn-remove")
			.html(__('Uncheck all'))
			.on("click", function() {
			$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
				if($(check).is(":checked")) {
					check.checked = false;
				}
			});
		});
		
		student_toolbar.find(".btn-mark-att")
			.html(__('Mark Attendence'))
			.on("click", function() {
				var students_present = [];
				var students_absent = [];
				$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if($(check).is(":checked")) {
						students_present.push(students[i]);
					}
					else {
						students_absent.push(students[i]);
					}
				});
				frappe.call({
					method: "erpnext.schools.api.mark_attendance",
					args: {
						"students_present": students_present,
						"students_absent": students_absent,
						"course_schedule": frm.doc.name
					},
					callback: function(r) {
						frm.events.view_attendance(frm)
					}
				});
		});

		
		$.each(students, function(i, m) {
			$(repl('<div class="col-sm-6">\
				<div class="checkbox">\
				<label><input type="checkbox" class="students-check" student="%(student)s">\
				%(student)s</label>\
			</div></div>', {student: m.student_name})).appendTo(me.wrapper);
		});
	}
})