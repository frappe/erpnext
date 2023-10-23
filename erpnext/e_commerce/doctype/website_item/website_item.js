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

		frm.add_custom_button(__("Save to Prom"), function() {
			frm.refresh();
			setTimeout(() => {frm.reload_doc();}, 500);

			setTimeout(() => {  
			frappe.call({
				method: "erpnext.e_commerce.doctype.website_item.website_item.save_to_prom_button",
				args: {doc: frm.doc},
				callback: function(result) {
					if (result) {
						frappe.show_alert({
							message:__('Successful saving'),
							indicator:'green'
						}, 5);
					} else {
						frappe.show_alert({
							message:__('Unexpected error'),
							indicator:'red'
						}, 5);
					}
				}
			}); }, 1000);

			
		}, __("Marketplaces"));
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
