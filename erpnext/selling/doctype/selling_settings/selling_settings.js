// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Selling Settings", {
<<<<<<< HEAD
	after_save(frm) {
		frappe.boot.user.defaults.editable_price_list_rate = frm.doc.editable_price_list_rate;
	},
=======
	refresh: function (frm) {},
>>>>>>> 7c4cf3e834 (Favicon.svg)
});
