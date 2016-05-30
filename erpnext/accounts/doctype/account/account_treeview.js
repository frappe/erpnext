frappe.treeview_settings["Account"] = {
	breadcrumbs: "Accounts",
	title: __("Chart Of Accounts"),
	get_tree_root: false,
	filters: [{
		fieldname: "comp",
		fieldtype:"Select",
		options: $.map(locals[':Company'], function(c) { return c.name; }).sort(),
		label: __("Company")
	}],
	root_label: "Accounts",
	get_tree_nodes: 'erpnext.accounts.page.accounts_browser.accounts_browser.get_children',
	add_tree_node: 'erpnext.accounts.utils.add_ac',
	menu_items:[
		{
			label: __('New Company'),
			action: function() { newdoc('Company'); },
			condition: 'frappe.boot.user.can_create.indexOf("Company") === -1'
		}
	],
	fields: [
		{fieldtype:'Data', fieldname:'account_name', label:__('New Account Name'), reqd:true,
			description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers")},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')},
		{fieldtype:'Select', fieldname:'root_type', label:__('Root Type'),
			options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
		},
		{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
			options: ['', 'Bank', 'Cash', 'Warehouse', 'Tax', 'Chargeable'].join('\n'),
			description: __("Optional. This setting will be used to filter in various transactions.") },
		{fieldtype:'Float', fieldname:'tax_rate', label:__('Tax Rate')},
		{fieldtype:'Link', fieldname:'warehouse', label:__('Warehouse'), options:"Warehouse"},
		{fieldtype:'Link', fieldname:'account_currency', label:__('Currency'), options:"Currency",
			description: __("Optional. Sets company's default currency, if not specified.")}
	]
}