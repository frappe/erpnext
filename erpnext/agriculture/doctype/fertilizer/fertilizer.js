// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fertilizer', {
	onload: (frm) => {
		if (frm.doc.fertilizer_contents == undefined) frm.call('load_contents');
	}
});
