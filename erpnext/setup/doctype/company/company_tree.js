frappe.treeview_settings["Company"] = {
	ignore_fields:["parent_company"],
	get_tree_nodes: 'erpnext.setup.doctype.company.company.get_children',
	add_tree_node: 'erpnext.setup.doctype.company.company.add_node',
	filters: [
		{
			fieldname: "company",
			fieldtype:"Link",
			options: "Company",
			label: __("Company"),
			get_query: function() {
				return {
					filters: [["Company", 'is_group', '=', 1]]
				};
			}
		},
	],
	breadcrumb: "Setup",
	root_label: "All Companies",
	get_tree_root: false,
	menu_items: [
		{
			label: __("New Company"),
			action: function() {
				frappe.new_doc("Company", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Company") !== -1'
		}
	],
	onload: function(treeview) {
		treeview.make_tree();
	}
};