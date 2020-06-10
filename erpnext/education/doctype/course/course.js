frappe.ui.form.on("Course", "refresh", function(frm) {
	if(!cur_frm.doc.__islocal) {
		frm.add_custom_button(__("Program"), function() {
			frappe.route_options = {
				"Program Course.course": frm.doc.name
			}
			frappe.set_route("List", "Program");
		});

		frm.add_custom_button(__("Student Group"), function() {
			frappe.route_options = {
				course: frm.doc.name
			}
			frappe.set_route("List", "Student Group");
		});

		frm.add_custom_button(__("Course Schedule"), function() {
			frappe.route_options = {
				course: frm.doc.name
			}
			frappe.set_route("List", "Course Schedule");
		});

		frm.add_custom_button(__("Assessment Plan"), function() {
			frappe.route_options = {
				course: frm.doc.name
			}
			frappe.set_route("List", "Assessment Plan");
		});
	}

	frm.set_query('default_grading_scale', function(){
		return {
			filters: {
				docstatus: 1
			}
		}
	});
});

frappe.ui.form.on('Course Topic', {
	topics_add: function(frm){
		frm.fields_dict['topics'].grid.get_field('topic').get_query = function(doc){
			var topics_list = [];
			if(!doc.__islocal) topics_list.push(doc.name);
			$.each(doc.topics, function(idx, val){
				if (val.topic) topics_list.push(val.topic);
			});
			return { filters: [['Topic', 'name', 'not in', topics_list]] };
		};
	}
});
