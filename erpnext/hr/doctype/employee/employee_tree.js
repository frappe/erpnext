frappe.treeview_settings['Employee'] = {
	get_tree_nodes: "erpnext.hr.doctype.employee.employee.get_children",
	filters: [
		{
			fieldname: "company",
			fieldtype:"Select",
			options: $.map(locals[':Company'], function(c) { return c.name; }).sort(),
			label: __("Company"),
			default: frappe.defaults.get_default('company') ? frappe.defaults.get_default('company') : ""
		}
	],
	breadcrumb: "Hr",
	disable_add_node: true,
	get_tree_root: false,
	toolbar: [
		{ toggle_btn: true },
		{
			label:__("Edit"),
			condition: function(node) {
				return !node.is_root;
			},
			click: function(node) {
				frappe.set_route("Form", "Employee", node.data.value);
			}
		}
	],
	menu_items: [
		{
			label: __("New Employee"),
			action: function() {
				frappe.new_doc("Employee", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Employee") !== -1'
		}
	],
};