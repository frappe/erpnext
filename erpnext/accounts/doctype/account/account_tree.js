frappe.provide("frappe.treeview_settings")

frappe.treeview_settings["Account"] = {
	breadcrumbs: "Accounts",
	title: __("Chart Of Accounts"),
	get_tree_root: false,
	filters: [{
		fieldname: "company",
		fieldtype:"Select",
		options: erpnext.utils.get_tree_options("company"),
		label: __("Company"),
		default: erpnext.utils.get_tree_default("company")
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
		{fieldtype:'Data', fieldname:'account_number', label:__('Account Number'),
			description: __("Number of new Account, it will be included in the account name as a prefix")},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')},
		{fieldtype:'Select', fieldname:'root_type', label:__('Root Type'),
			options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
			depends_on: 'eval:doc.is_group && !doc.parent_account'},
		{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
			options: frappe.get_meta("Account").fields.filter(d => d.fieldname=='account_type')[0].options,
			description: __("Optional. This setting will be used to filter in various transactions.")
		},
		{fieldtype:'Float', fieldname:'tax_rate', label:__('Tax Rate'),
			depends_on: 'eval:doc.is_group==0&&doc.account_type=="Tax"'},
		{fieldtype:'Link', fieldname:'account_currency', label:__('Currency'), options:"Currency",
			description: __("Optional. Sets company's default currency, if not specified.")}
	],
	ignore_fields:["parent_account"],
	onload: function(treeview) {
		frappe.treeview_settings['Account'].page = {};
		$.extend(frappe.treeview_settings['Account'].page, treeview.page);
		function get_company() {
			return treeview.page.fields_dict.company.get_value();
		}

		// tools
		treeview.page.add_inner_button(__("Chart of Cost Centers"), function() {
			frappe.set_route('Tree', 'Cost Center', {company: get_company()});
		}, __('View'));

		treeview.page.add_inner_button(__("Opening Invoice Creation Tool"), function() {
			frappe.set_route('Form', 'Opening Invoice Creation Tool', {company: get_company()});
		}, __('View'));

		treeview.page.add_inner_button(__("Period Closing Voucher"), function() {
			frappe.set_route('List', 'Period Closing Voucher', {company: get_company()});
		}, __('View'));

		// make
		treeview.page.add_inner_button(__("Journal Entry"), function() {
			frappe.new_doc('Journal Entry', {company: get_company()});
		}, __('Make'));
		treeview.page.add_inner_button(__("New Company"), function() {
			frappe.new_doc('Company');
		}, __('Make'));

		// financial statements
		for (let report of ['Trial Balance', 'General Ledger', 'Balance Sheet',
			'Profit and Loss Statement', 'Cash Flow Statement', 'Accounts Payable', 'Accounts Receivable']) {
			treeview.page.add_inner_button(__(report), function() {
				frappe.set_route('query-report', report, {company: get_company()});
			}, __('Financial Statements'));
		}

	},
	onrender: function(node) {
		if(frappe.boot.user.can_read.indexOf("GL Entry") !== -1){
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
					"company": frappe.treeview_settings['Account'].page.fields_dict.company.get_value()
				};
				frappe.set_route("query-report", "General Ledger");
			},
			btnClass: "hidden-xs"
		}
	],
	extend_toolbar: true
}
