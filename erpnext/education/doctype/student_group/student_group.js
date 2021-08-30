cur_frm.add_fetch('student', 'title', 'student_name');

frappe.ui.form.on('Student Group', {
	onload: function(frm) {
		frm.set_query('academic_term', function() {
			return {
				filters: {
					'academic_year': (frm.doc.academic_year)
				}
			};
		});
		if (!frm.__islocal) {
			frm.set_query('student', 'students', function() {
				return{
					query: 'erpnext.education.doctype.student_group.student_group.fetch_students',
					filters: {
						'academic_year': frm.doc.academic_year,
						'group_based_on': frm.doc.group_based_on,
						'academic_term': frm.doc.academic_term,
						'program': frm.doc.program,
						'batch': frm.doc.batch,
						'student_category': frm.doc.student_category,
						'course': frm.doc.course,
						'student_group': frm.doc.name
					}
				}
			});
		}
	},

	refresh: function(frm) {
		if (!frm.doc.__islocal) {

			frm.add_custom_button(__('Add Guardians to Email Group'), function() {
				frappe.call({
					method: 'erpnext.education.api.update_email_group',
					args: {
						'doctype': 'Student Group',
						'name': frm.doc.name
					}
				});
			}, __('Actions'));

			frm.add_custom_button(__('Student Attendance Tool'), function() {
				frappe.route_options = {
					based_on: 'Student Group',
					student_group: frm.doc.name
				}
				frappe.set_route('Form', 'Student Attendance Tool', 'Student Attendance Tool');
			}, __('Tools'));

			frm.add_custom_button(__('Course Scheduling Tool'), function() {
				frappe.route_options = {
					student_group: frm.doc.name
				}
				frappe.set_route('Form', 'Course Scheduling Tool', 'Course Scheduling Tool');
			}, __('Tools'));

			frm.add_custom_button(__('Newsletter'), function() {
				frappe.route_options = {
					'Newsletter Email Group.email_group': frm.doc.name
				}
				frappe.set_route('List', 'Newsletter');
			}, __('View'));

		}
	},

	group_based_on: function(frm) {
		if (frm.doc.group_based_on == 'Batch') {
			frm.doc.course = null;
			frm.set_df_property('program', 'reqd', 1);
			frm.set_df_property('course', 'reqd', 0);
		}
		else if (frm.doc.group_based_on == 'Course') {
			frm.set_df_property('program', 'reqd', 0);
			frm.set_df_property('course', 'reqd', 1);
		}
		else if (frm.doc.group_based_on == 'Activity') {
			frm.set_df_property('program', 'reqd', 0);
			frm.set_df_property('course', 'reqd', 0);
		}
	},

	get_students: function(frm) {
		if (frm.doc.group_based_on == 'Batch' || frm.doc.group_based_on == 'Course') {
			var student_list = [];
			var max_roll_no = 0;
			$.each(frm.doc.students, function(_i,d) {
				student_list.push(d.student);
				if (d.group_roll_number>max_roll_no) {
					max_roll_no = d.group_roll_number;
				}
			});

			if (frm.doc.academic_year) {
				frappe.call({
					method: 'erpnext.education.doctype.student_group.student_group.get_students',
					args: {
						'academic_year': frm.doc.academic_year,
						'academic_term': frm.doc.academic_term,
						'group_based_on': frm.doc.group_based_on,
						'program': frm.doc.program,
						'batch' : frm.doc.batch,
						'student_category' : frm.doc.student_category,
						'course': frm.doc.course
					},
					callback: function(r) {
						if (r.message) {
							$.each(r.message, function(i, d) {
								if(!in_list(student_list, d.student)) {
									var s = frm.add_child('students');
									s.student = d.student;
									s.student_name = d.student_name;
									if (d.active === 0) {
										s.active = 0;
									}
									s.group_roll_number = ++max_roll_no;
								}
							});
							refresh_field('students');
							frm.save();
						} else {
							frappe.msgprint(__('Student Group is already updated.'))
						}
					}
				})
			}
		} else {
			frappe.msgprint(__('Select students manually for the Activity based Group'));
		}
	}
});

frappe.ui.form.on('Student Group Instructor', {
	instructors_add: function(frm){
		frm.fields_dict['instructors'].grid.get_field('instructor').get_query = function(doc){
			let instructor_list = [];
			$.each(doc.instructors, function(idx, val){
				instructor_list.push(val.instructor);
			});
			return { filters: [['Instructor', 'name', 'not in', instructor_list]] };
		};
	}
});
