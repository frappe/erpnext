
// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("assessment_plan", "student_group", "student_group");

frappe.ui.form.on('Assessment Result Tool', {
	refresh: function(frm) {
		frm.trigger("assessment_plan");
		if (frappe.route_options) {
			frm.set_value("student_group", frappe.route_options.student_group);
			frm.set_value("assessment_plan", frappe.route_options.assessment_plan);
			frappe.route_options = null;
		}
		frm.disable_save();
		frm.page.clear_indicator();
	},

	assessment_plan: function(frm) {
		if(!frm.doc.student_group) return;
		frappe.call({
			method: "erpnext.schools.api.get_assessment_students",
			args: {
				"assessment_plan": frm.doc.assessment_plan,
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
				var criteria_list = r.message;
				var max_total_score = 0;
				criteria_list.forEach(function(c) {
					max_total_score += c.maximum_score
				});
				var result_table = $(frappe.render_template('assessment_result_tool', {
					frm: frm,
					students: students,
					criteria: criteria_list,
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
					if(Object.keys(student_scores[student]).length == criteria_list.length) {
						console.log("ok");
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
										return d.assessment_criteria === criteria;
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
