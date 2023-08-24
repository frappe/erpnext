// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Reposting Settings', {
	refresh: function(frm) {
		frm.trigger('convert_to_item_based_reposting');
	},

	convert_to_item_based_reposting: function(frm) {
		frm.add_custom_button(__('Convert to Item Based Reposting'), function() {
			frm.call({
				method: 'convert_to_item_wh_reposting',
				frezz: true,
				doc: frm.doc,
				callback: function(r) {
					if (!r.exc) {
						frm.reload_doc();
					}
				}
			})
		})
	}
});
