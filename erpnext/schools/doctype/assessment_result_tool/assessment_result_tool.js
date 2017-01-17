// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("assessment_plan", "student_group", "student_group");
cur_frm.add_fetch("assessment_plan", "student_batch", "student_batch");

frappe.ui.form.on('Assessment Result Tool', {
    refresh: function(frm) {
       frm.disable_save();
	   frm.page.clear_indicator();
    },

	assessment_plan: function(frm) {
		if(!(frm.doc.student_batch || frm.doc.student_group)) return;
		frappe.call({
			method: "erpnext.schools.api.get_assessment_students",
			args: {
				"assessment_plan": frm.doc.assessment_plan,
				"student_batch": frm.doc.student_batch,
				"student_group": frm.doc.student_group
			},
			callback: function(r) {
				frm.events.render_table(frm, r.message);
			}
		});
	},

	render_table: function(frm, students) {
		$(frm.fields_dict.result_html.wrapper).empty();
		var assessment_plan = frm.doc.assessment_plan;
		var student_scores = {};
		students.forEach(function(stu) {
			student_scores[stu.student] = {}
		});
		
		frappe.call({
			method: "erpnext.schools.api.get_assessment_details",
			args: {
				assessment_plan: assessment_plan
			},
			callback: function(r) {
				var criterias = r.message;
				var max_total_score = 0;
				criterias.forEach(function(c) {
					max_total_score += c.maximum_score
				});
				var result_table = $(frappe.render_template('assessment_result_tool', {
					frm: frm,
					students: students,
					criterias: criterias,
					max_total_score: max_total_score
				}));
				result_table.appendTo(frm.fields_dict.result_html.wrapper)

				result_table.on('change', 'input', function(e) {
					var $input = $(e.target);
					var max_score = $input.data().maxScore;
					var student = $input.data().student;
					var criteria = $input.data().criteria;
					var value = $input.val();
					if(value < 0) {
						$input.val(0);
						value = 0;
					}
					if(value > max_score) {
						$input.val(max_score);
						value = max_score;
					}
					student_scores[student][criteria] = value;
					if(Object.keys(student_scores[student]).length == criterias.length) {
						frappe.call(({
							method: "erpnext.schools.api.mark_assessment_result",
							args: {
								"student": student,
								"assessment_plan": assessment_plan,
								"scores": student_scores[student]
							},
							callback: function(r) {
								var doc = r.message;
								var student = doc.student;
								result_table.find(`[data-student=${student}].total-score`)
									.html(doc.total_score + ' ('+ doc.grade + ')');
								var details = doc.details;
								result_table.find(`tr[data-student=${student}]`).addClass('text-muted');
								result_table.find(`input[data-student=${student}]`).each(function(el, input) {
									var $input = $(input);
									var criteria = $input.data().criteria;
									var value = $input.val();
									var grade = details.find(function(d) {
										return d.evaluation_criteria === criteria;
									}).grade;
									$input.val(`${value} (${grade})`);
									$input.attr('disabled', true);
								});

							}
						}))
					}
				});

			}
		});
	},

});
