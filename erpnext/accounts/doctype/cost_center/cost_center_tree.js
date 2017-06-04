frappe.treeview_settings["Cost Center"] = {
	breadcrumbs: "Accounts",
	get_tree_root: false,
	filters: [{
		fieldname: "company",
		fieldtype:"Select",
		options: $.map(locals[':Company'], function(c) { return c.name; }).sort(),
		label: __("Company"),
		default: frappe.defaults.get_default('company') ? frappe.defaults.get_default('company'): ""
	}],
	root_label: "Cost Centers",
	get_tree_nodes: 'erpnext.accounts.utils.get_children',
	add_tree_node: 'erpnext.accounts.utils.add_cc',
	menu_items:[
		{
			label: __('New Company'),
			action: function() { frappe.new_doc("Company", true) },
			condition: 'frappe.boot.user.can_create.indexOf("Company") !== -1'
		}
	],
	fields:[
		{fieldtype:'Data', fieldname:'cost_center_name', label:__('New Cost Center Name'), reqd:true},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description:__('Further cost centers can be made under Groups but entries can be made against non-Groups')}
	],
	ignore_fields:["parent_cost_center"]
}