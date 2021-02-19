// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Website Item', {
	image: function() {
		refresh_field("image_view");
	},

	copy_from_item_group: function(frm) {
		return frm.call({
			doc: frm.doc,
			method: "copy_specification_from_item_group"
		});
	},

	set_meta_tags(frm) {
		frappe.utils.set_meta_tag(frm.doc.route);
	}
});
