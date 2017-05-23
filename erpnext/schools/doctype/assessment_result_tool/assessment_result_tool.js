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
		frm.page.set_primary_action(__("Save Result"), function() {
			console.log("Marks Submitted")
			frm.events.make_result(frm)
		});
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
				frm.doc.students = r.message;
				frm.events.render_table(frm);
			}
		});
	},

	render_table: function(frm) {
		$(frm.fields_dict.result_html.wrapper).empty();
		var assessment_plan = frm.doc.assessment_plan;
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
					students: frm.doc.students,
					criteria: criteria_list,
					max_total_score: max_total_score
				}));
				result_table.appendTo(frm.fields_dict.result_html.wrapper);
				result_table.on('change', 'input', function(e) {
					var $input = $(e.target);
					var student = $input.data().student;
					var max_score = $input.data().maxScore;
					var value = $input.val();
					if(value < 0) {
						$input.val(0);
						value = 0;
					} else if(value > max_score) {
						$input.val(max_score);
						value = max_score;
					}
					var total_score = 0;
					result_table.find(`input[data-student=${student}]`).each(function(el, input) {
						var $input = $(input);
						total_score += parseFloat($input.val());
					});
					if(!isNaN(total_score)) {
						console.log("ok");
						result_table.find(`[data-student=${student}].total-score`)
							.html(total_score);
					}
				});
			}
		});
	},

	make_result: function(frm) {
		var student_scores = {};
		frm.doc.students.forEach(function(stu) {
			student_scores[stu.student] = {}
			var result_table = $(frm.fields_dict.result_html.wrapper);
			result_table.find(`input[data-student=${stu.student}]`).each(function(el, input) {
				var $input = $(input);
				var criteria = $input.data().criteria;
				var value = parseFloat($input.val());
				if (value) {
					student_scores[stu.student][criteria] = value;
				}
			});
			result_table.find(`[data-student=${stu.student}].total-score`).each(function(el, input){
				student_scores[stu.student]["total_score"] = parseFloat($(input).html());
			})
		});
		Object.keys(student_scores).forEach(function(key){
			if (isNaN(student_scores[key]["total_score"])){
				delete student_scores[key];
			}
		});
		console.log(student_scores);
		frappe.call(({
			method: "erpnext.schools.api.mark_assessment_result",
			args: {
				"assessment_plan": frm.doc.assessment_plan,
				"scores": student_scores
			},
			callback: function(r) {
				console.log(r);
			}
		}))
		
	}

});
