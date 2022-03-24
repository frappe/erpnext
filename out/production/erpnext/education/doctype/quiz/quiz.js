// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quiz', {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Add to Topics'), function() {
				frm.trigger('add_quiz_to_topics');
			}, __('Action'));
		}
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
			frappe.throw(__('The question cannot be duplicate'));
		}
	},

	add_quiz_to_topics: function(frm) {
		get_topics_without_quiz(frm.doc.name).then(r => {
			if (r.message.length) {
				frappe.prompt([
					{
						fieldname: 'topics',
						label: __('Topics'),
						fieldtype: 'MultiSelectPills',
						get_data: function() {
							return r.message;
						}
					}
				],
				function(data) {
					frappe.call({
						method: 'erpnext.education.doctype.topic.topic.add_content_to_topics',
						args: {
							'content_type': 'Quiz',
							'content': frm.doc.name,
							'topics': data.topics,
						},
						callback: function(r) {
							if (!r.exc) {
								frm.reload_doc();
							}
						},
						freeze: true,
						freeze_message: __('...Adding Quiz to Topics')
					});
				}, __('Add Quiz to Topics'), __('Add'));
			} else {
				frappe.msgprint(__('This quiz is already added to the existing topics'));
			}
		});
	}
});

let get_topics_without_quiz = function(quiz) {
	return frappe.call({
		type: 'GET',
		method: 'erpnext.education.doctype.quiz.quiz.get_topics_without_quiz',
		args: {'quiz': quiz}
	});
};
