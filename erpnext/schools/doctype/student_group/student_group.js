cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Student Group", {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__("Course Schedule"), function() {
				frappe.route_options = {
					student_group: frm.doc.name
				}
				frappe.set_route("List", "Course Schedule");
			});
		
			frm.add_custom_button(__("Assessment"), function() {
				frappe.route_options = {
					student_group: frm.doc.name
				}
				frappe.set_route("List", "Assessment");
			});
		}
	},
	
	onload: function(frm){
		cur_frm.set_query("academic_term",function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
		
		cur_frm.set_query("student_batch", function(){
			return{
				"filters": {
					"active": 1
				}
			};
		});
	}	
});

//If Student Batch is entered, deduce program, academic_year and academic term from it
cur_frm.add_fetch("student_batch", "program", "program");
cur_frm.add_fetch("student_batch", "academic_term", "academic_term");
cur_frm.add_fetch("student_batch", "academic_year", "academic_year");
