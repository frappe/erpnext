frappe.provide("frappe.treeview_settings")

frappe.treeview_settings["Account"] = {
	breadcrumbs: "Accounts",
	title: __("Chart Of Accounts"),
	get_tree_root: false,
	filters: [{
		fieldname: "company",
		fieldtype:"Select",
		options: $.map(locals[':Company'], function(c) { return c.name; }).sort(),
		label: __("Company"),
		default: frappe.defaults.get_default('company') ? frappe.defaults.get_default('company'): ""
	}],
	root_label: "Accounts",
	get_tree_nodes: 'erpnext.accounts.utils.get_children',
	add_tree_node: 'erpnext.accounts.utils.add_ac',
	menu_items:[
		{
			label: __('New Company'),
			action: function() { frappe.new_doc("Company", true) },
			condition: 'frappe.boot.user.can_create.indexOf("Company") !== -1'
		}
	],
	fields: [
		{fieldtype:'Data', fieldname:'account_name', label:__('New Account Name'), reqd:true,
			description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers")},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')},
		{fieldtype:'Select', fieldname:'root_type', label:__('Root Type'),
			options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
			depends_on: 'eval:doc.is_group && !doc.parent_account'},
		{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
			options: ['', 'Accumulated Depreciation', 'Bank', 'Cash', 'Chargeable', 'Cost of Goods Sold', 'Depreciation',
				'Equity', 'Expense Account', 'Expenses Included In Valuation', 'Fixed Asset', 'Income Account', 'Payable', 'Receivable',
				'Round Off', 'Stock', 'Stock Adjustment', 'Stock Received But Not Billed', 'Tax', 'Temporary'].join('\n'),
			description: __("Optional. This setting will be used to filter in various transactions.")
		},
		{fieldtype:'Float', fieldname:'tax_rate', label:__('Tax Rate'),
			depends_on: 'eval:doc.is_group==0&&doc.account_type=="Tax"'},
		{fieldtype:'Link', fieldname:'account_currency', label:__('Currency'), options:"Currency",
			description: __("Optional. Sets company's default currency, if not specified.")}
	],
	ignore_fields:["parent_account"],
	onrender: function(node) {
		var dr_or_cr = node.data.balance < 0 ? "Cr" : "Dr";
		if (node.data && node.data.balance!==undefined) {
			$('<span class="balance-area pull-right text-muted small">'
				+ (node.data.balance_in_account_currency ?
					(format_currency(Math.abs(node.data.balance_in_account_currency),
						node.data.account_currency) + " / ") : "")
				+ format_currency(Math.abs(node.data.balance), node.data.company_currency)
				+ " " + dr_or_cr
				+ '</span>').insertBefore(node.$ul);
		}
	},
	toolbar: [
		{
			condition: function(node) {
				return !node.root && frappe.boot.user.can_read.indexOf("GL Entry") !== -1
			},
			label: __("View Ledger"),
			click: function(node, btn) {
				frappe.route_options = {
					"account": node.label,
					"from_date": frappe.sys_defaults.year_start_date,
					"to_date": frappe.sys_defaults.year_end_date,
					"company": frappe.defaults.get_default('company') ? frappe.defaults.get_default('company'): ""
				};
				frappe.set_route("query-report", "General Ledger");
			},
			btnClass: "hidden-xs"
		}
	],
	extend_toolbar: true
}
