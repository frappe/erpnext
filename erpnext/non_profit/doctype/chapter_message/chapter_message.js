// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Chapter Message', {
	onload: function(frm){
		console.log("here" + frappe.session.user)
		chapter_head = frappe.session.user
		frappe.db.get_value('Chapter', {chapter_head: chapter_head}, 'name', function(data) {
		  frm.set_value('chapter', data.name);
		})
	},
});
