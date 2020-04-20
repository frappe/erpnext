frappe.treeview_settings["Cost Center"] = {
	breadcrumb: "Accounts",
	get_tree_root: false,
	filters: [{
		fieldname: "company",
		fieldtype:"Select",
		options: erpnext.utils.get_tree_options("company"),
		label: __("Company"),
		default: erpnext.utils.get_tree_default("company")
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
			description:__('Further cost centers can be made under Groups but entries can be made against non-Groups')},
		{fieldtype:'Data', fieldname:'cost_center_number', label:__('Cost Center Number'),
			description: __("Number of new Cost Center, it will be included in the cost center name as a prefix")}
	],
	ignore_fields:["parent_cost_center"],
	onload: function(treeview) {
		function get_company() {
			return treeview.page.fields_dict.company.get_value();
		}

		// tools
		treeview.page.add_inner_button(__("Chart of Accounts"), function() {
			frappe.set_route('Tree', 'Account', {company: get_company()});
		}, __('View'));

		// make
		treeview.page.add_inner_button(__("Budget List"), function() {
			frappe.set_route('List', 'Budget', {company: get_company()});
		}, __('Budget'));

		treeview.page.add_inner_button(__("Monthly Distribution"), function() {
			frappe.set_route('List', 'Monthly Distribution', {company: get_company()});
		}, __('Budget'));

		treeview.page.add_inner_button(__("Budget Variance Report"), function() {
			frappe.set_route('query-report', 'Budget Variance Report', {company: get_company()});
		}, __('Budget'));

	}

}