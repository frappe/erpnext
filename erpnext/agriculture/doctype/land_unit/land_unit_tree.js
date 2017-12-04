frappe.treeview_settings["Land Unit"] = {
	ignore_fields:["parent_land_unit"],
	disable_add_node: true,
	toolbar: [
		{ toggle_btn: true },
		{
			label:__("Add Child"),
			click: function(node) {
				var lu = frappe.new_doc("Land Unit", {
					"parent_land_unit": node.label
				})
			}
		}
	],
}