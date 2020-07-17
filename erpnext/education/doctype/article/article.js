// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Article', {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Add to Topics'), function() {
				frm.trigger('add_article_to_topics');
			}, __('Action'));
		}
	},

	add_article_to_topics: function(frm) {
		get_topics_without_article(frm.doc.name).then(r => {
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
							'content_type': 'Article',
							'content': frm.doc.name,
							'topics': data.topics,
						},
						callback: function(r) {
							if (!r.exc) {
								frm.reload_doc();
							}
						},
						freeze: true,
						freeze_message: __('...Adding Article to Topics')
					});
				}, __('Add Article to Topics'), __('Add'));
			} else {
				frappe.msgprint(__('This article is already added to the existing topics'));
			}
		});
	}
});

let get_topics_without_article = function(article) {
	return frappe.call({
		type: 'GET',
		method: 'erpnext.education.doctype.article.article.get_topics_without_article',
		args: {'article': article}
	});
};