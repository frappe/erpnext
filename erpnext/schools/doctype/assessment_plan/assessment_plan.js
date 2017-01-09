// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("student_group", "course", "course");
cur_frm.add_fetch("student_group", "student_batch", "student_batch");
cur_frm.add_fetch("examiner", "instructor_name", "examiner_name");
cur_frm.add_fetch("supervisor", "instructor_name", "supervisor_name");

frappe.ui.form.on("Assessment Plan", {
    course: function(frm) {
        if (frm.doc.course && frm.doc.maximum_assessment_score) {
            frappe.call({
                method: "erpnext.schools.api.get_evaluation_criterias",
                args: {
                    course: frm.doc.course
                },
                callback: function(r) {
                    if (r.message) {
                        frm.doc.evaluation_criterias = [];
                        $.each(r.message, function(i, d) {
                            var row = frappe.model.add_child(frm.doc, "Assessment Evaluation Criteria", "evaluation_criterias");
                            row.evaluation_criteria = d.evaluation_criteria;
                            row.maximum_score = d.weightage / 100 * frm.doc.maximum_assessment_score;
                        });
                    }
                    refresh_field("evaluation_criterias");

                }
            });
        }
    },

    maximum_assessment_score: function(frm) {
        frm.trigger("course");
    }
});