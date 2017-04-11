// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Item Group", {
	onload: function(frm) {
		frm.list_route = "Tree/Item Group";

		//get query select item group
		frm.fields_dict['parent_item_group'].get_query = function(doc,cdt,cdn) {
			return{
				filters:[
					['Item Group', 'is_group', '=', 1],
					['Item Group', 'name', '!=', doc.item_group_name]
				]
			}
		}
	},

	refresh: function(frm) {
		frm.trigger("set_root_readonly");
		frm.add_custom_button(__("Item Group Tree"), function() {
			frappe.set_route("Tree", "Item Group");
		});

		if(!frm.is_new()) {
			frm.add_custom_button(__("Items"), function() {
				frappe.set_route("List", "Item", {"item_group": frm.doc.name});
			});
		}
	},

	set_root_readonly: function(frm) {
		// read-only for root item group
		frm.set_intro("");
		if(!frm.doc.parent_item_group) {
			frm.set_read_only();
			frm.set_intro(__("This is a root item group and cannot be edited."), true);
		}
	},

	page_name: frappe.utils.warn_page_name_change
});
