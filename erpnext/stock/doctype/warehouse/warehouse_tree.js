frappe.treeview_settings['Warehouse'] = {
	get_tree_nodes: "erpnext.stock.doctype.warehouse.warehouse.get_children",
	add_tree_node: "erpnext.stock.doctype.warehouse.warehouse.add_node",
	get_tree_root: false,
	root_label: "Warehouses",
	filters: [{
		fieldname: "company",
		fieldtype:"Select",
		options: $.map(locals[':Company'], function(c) { return c.name; }).sort(),
		label: __("Company"),
		default: frappe.defaults.get_default('company') ? frappe.defaults.get_default('company'): ""
	}],
	fields:[
		{fieldtype:'Data', fieldname: 'warehouse_name',
			label:__('New Warehouse Name'), reqd:true},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description: __("Child nodes can be only created under 'Group' type nodes")}
	],
	ignore_fields:["parent_warehouse"],
	onrender: function(node) {
		if (node.data && node.data.balance!==undefined) {
			$('<span class="balance-area pull-right text-muted small">'
			+ format_currency(Math.abs(node.data.balance), node.data.company_currency)
			+ '</span>').insertBefore(node.$ul);
		}
	}
}