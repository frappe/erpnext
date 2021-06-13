frappe.provide("education");

cur_frm.add_fetch("student_group", "course", "course")
frappe.ui.form.on("Schedule Subject Lecture", {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Mark Attendance"), function() {
				frappe.route_options = {
					based_on: "Schedule Subject Lecture",
					course_schedule: frm.doc.name
				}
				frappe.set_route("Form", "Student Attendance Tool");
			}).addClass("btn-primary");
		}
	},
	course:function(frm){
		if(!frm.doc.student_group){
			frappe.throw('Enter Group name')
		}
		// else{
		// 	frm.set_query('course',()=> {
		// 		return {
		// 			query: 'erpnext.education.doctype.course_schedule.course_schedule.get_subjects',
		// 			filters:{
		// 				group_name:frm.doc.student_group
		// 			}	
					
		// 	}})
		// }

	},
	student_group:function(frm){
		if(frm.doc.student_group){
			frm.set_query('course',()=> {
				return {
					query: 'erpnext.education.doctype.schedule_subject_lecture.schedule_subject_lecture.get_subjects',
					filters:{
						group_name:frm.doc.student_group
					}	
					
			}})
			

		}
	}
});