frappe.ui.form.on("Student Group Creation Tool", "refresh", function(frm) {
	frm.disable_save();
	frm.page.set_primary_action(__("Create Student Groups"), function() {
		frappe.call({
			method: "create_student_groups",
			doc:frm.doc
		})
	});
	frappe.realtime.on("student_group_creation_progress", function(data) {
		if(data.progress) {
			frappe.hide_frappe.msgprint(true);
			frappe.show_progress(__("Creating student groups"), data.progress[0],data.progress[1]);
		}
	});
});

frappe.ui.form.on("Student Group Creation Tool", "get_courses", function(frm) {
	frm.set_value("courses",[]);
	if (frm.doc.academic_year && frm.doc.program) {
		frappe.call({
			method: "get_courses",
			doc:frm.doc,
			callback: function(r) {
				if(r.message) {
					frm.set_value("courses", r.message);
				}
			}
		})
	}
});

frappe.ui.form.on("Student Group Creation Tool", "onload", function(frm){
	cur_frm.set_query("academic_term",function(){
		return{
			"filters":{
				"academic_year": (frm.doc.academic_year)
			}
		};
	});
});