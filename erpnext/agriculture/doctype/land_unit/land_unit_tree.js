frappe.treeview_settings["Land Unit"] = {
	get_tree_nodes: "erpnext.agriculture.doctype.land_unit.land_unit.get_children",
	ignore_fields:["parent_land_unit"],
	get_tree_root: false,
	disable_add_node: true,
	root_label: "All Land Units",
	onload: function(me) {
		me.make_tree();
	},
	toolbar: [
		{ toggle_btn: true },
		{
			label:__("Edit"),
			condition: function(node) { return (node.label!='All Land Units'); },
			click: function(node) {
				frappe.set_route('Form', 'Land Unit', node.data.value);
			}
		},
		{
			label:__("Add Child"),
			condition: function(node) { return node.expandable; },
			click: function(node) {
				if(node.label=='All Land Units') node.label='';
				var lu = frappe.new_doc("Land Unit", {
					"parent_land_unit": node.label
				});
			}
		}
	],
};