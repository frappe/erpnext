// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("student_group", "course", "course");
cur_frm.add_fetch("examiner", "instructor_name", "examiner_name");
cur_frm.add_fetch("supervisor", "instructor_name", "supervisor_name");

frappe.ui.form.on("Assessment Plan", {

    onload: function(frm) {
        frm.set_query("assessment_group", function(doc, cdt, cdn) {
            return{
                filters: {
                    'is_group': 0
                }
            }
        });
    },

    refresh: function(frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__("Assessment Result"), function() {
                frappe.route_options = {
                    assessment_plan: frm.doc.name,
                    student_group: frm.doc.student_group
                }
                frappe.set_route("Form", "Assessment Result Tool");
            });
        }

        frm.set_df_property("courses_section", "hidden", frm.doc.multiple_courses == 0);
        frm.set_df_property("course", "hidden", frm.doc.multiple_courses==1);

    },

	course: function(frm) {
		if (frm.doc.course && frm.doc.maximum_assessment_score) {
			frappe.call({
				method: "erpnext.schools.api.get_assessment_criteria",
				args: {
					course: frm.doc.course
				},
				callback: function(r) {
					if (r.message) {
						frm.doc.assessment_criteria = [];
						$.each(r.message, function(i, d) {
							var row = frappe.model.add_child(frm.doc, "Assessment Plan Criteria", "assessment_criteria");
							row.assessment_criteria = d.assessment_criteria;
							row.maximum_score = d.weightage / 100 * frm.doc.maximum_assessment_score;
						});
					}
					refresh_field("assessment_criteria");

				}
			});
		}
	},

    multiple_courses: function(frm) {
        frm.set_df_property("course", "hidden", frm.doc.multiple_courses==1);
        frm.set_df_property("courses_section", "hidden", frm.doc.multiple_courses == 0);
        frm.set_df_property("course", "reqd", frm.doc.multiple_courses==0);
    },

    get_courses: function(frm) {
        console.log("######   CALLED    #########");
        frm.set_value("courses_table",[]);
        frappe.call({
            method: "erpnext.schools.api.get_courses",
            args: {"student_group": frm.doc.student_group},
            callback: function(r) {
                console.log("######   CALLBACK RESULT    #########");
                console.log(r.message);
                frm.set_value("courses_table",r.message)
                frm.trigger("default_course");
            }
        })
    },

    default_course: function(frm) {
        frm.set_value("course", frm.doc.courses_table[0].course_link);
    },

	maximum_assessment_score: function(frm) {
		frm.trigger("course");
	}
});