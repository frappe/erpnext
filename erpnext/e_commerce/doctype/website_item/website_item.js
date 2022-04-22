// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Website Item', {
	onload: (frm) => {
		// should never check Private
		frm.fields_dict["website_image"].df.is_private = 0;

		frm.set_query("website_warehouse", () => {
			return {
				filters: {"is_group": 0}
			};
		});
	},

	refresh: (frm) => {
		frm.add_custom_button(__("Prices"), function() {
			frappe.set_route("List", "Item Price", {"item_code": frm.doc.item_code});
		}, __("View"));

		frm.add_custom_button(__("Stock"), function() {
			frappe.route_options = {
				"item_code": frm.doc.item_code
			};
			frappe.set_route("query-report", "Stock Balance");
		}, __("View"));

		frm.add_custom_button(__("E Commerce Settings"), function() {
			frappe.set_route("Form", "E Commerce Settings");
		}, __("View"));
	},

	image: () => {
		refresh_field("image_view");
	},

	copy_from_item_group: (frm) => {
		return frm.call({
			doc: frm.doc,
			method: "copy_specification_from_item_group"
		});
	},

	set_meta_tags: (frm) => {
		frappe.utils.set_meta_tag(frm.doc.route);
	}
});
