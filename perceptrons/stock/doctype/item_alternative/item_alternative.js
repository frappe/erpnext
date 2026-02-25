// Copyright (c) 2018, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Alternative", {
	setup: function (frm) {
		frm.fields_dict.item_code.get_query = () => {
			return {
				filters: {
					allow_alternative_item: 1,
				},
			};
		};
	},
});
