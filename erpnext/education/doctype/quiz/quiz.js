// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quiz', {
	refresh: function(frm) {

	},
	validate: function(frm){
		frm.events.check_duplicate_question(frm.doc.question);
	},
	check_duplicate_question: function(questions_data){
		var questions = [];
		questions_data.forEach(function(q){
			questions.push(q.question_link);
		});
		var questions_set = new Set(questions);
		if (questions.length != questions_set.size) {
			frappe.throw(__("The question cannot be duplicate"));
		}
	}
});