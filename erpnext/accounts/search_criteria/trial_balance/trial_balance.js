report.customize_filters = function() {
	this.hide_all_filters();

	this.add_filter({fieldname:'show_group_ledger', label:'Show Group/Ledger', fieldtype:'Select', options:'Only Groups'+NEWLINE+'Only Ledgers'+NEWLINE+'Both But Without Group Balance'+NEWLINE+'Both With Balance',ignore : 1, parent:'Account', 'report_default':'Both With Balance','in_first_page':1,single_select:1});
	
	this.add_filter({fieldname:'show_zero_balance', label:'Show Zero Balance', fieldtype:'Select', options:'Yes'+NEWLINE+'No',ignore : 1, parent:'Account', 'report_default':'Yes','in_first_page':1,single_select:1});
	
	this.add_filter({fieldname:'transaction_date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'Account', 'in_first_page':1});

	this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df.filter_hide = 0;
	this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df.filter_hide = 0;
	this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df.filter_hide = 0;

	this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df['report_default'] = sys_defaults.year_start_date;
	this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df['report_default'] = dateutil.obj_to_str(new Date());
	this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;

	this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df.in_first_page = 1;
	this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df.in_first_page = 1;
	this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df.in_first_page = 1;

	this.dt.set_no_limit(1);
}

report.aftertableprint = function(t) {
	 $yt(t,'*',1,{whiteSpace:'pre'});
}

$dh(this.mytabs.tabs['More Filters']);
$dh(this.mytabs.tabs['Select Columns']);

report.get_query = function() {
	var g_or_l = this.get_filter('Account', 'Show Group/Ledger').get_value();
	var comp = this.get_filter('Account', 'Company').get_value();
	
	if (g_or_l == 'Only Ledgers') {
		var q = "SELECT name FROM tabAccount WHERE group_or_ledger = 'Ledger' and company = '" + comp + "' and docstatus != 2 ORDER BY lft";
	} else if (g_or_l == 'Only Groups') {
		var q = "SELECT CONCAT( REPEAT('   ', COUNT(parent.name) - 1), node.name) AS name FROM tabAccount AS node,tabAccount AS parent WHERE (node.lft BETWEEN parent.lft AND parent.rgt) and node.group_or_ledger = 'Group' and node.company = '" + comp + "' and node.docstatus != 2 GROUP BY node.name ORDER BY node.lft";
	} else {
		var q = "SELECT CONCAT( REPEAT('   ', COUNT(parent.name) - 1), node.name) AS name FROM tabAccount AS node,tabAccount AS parent WHERE node.lft BETWEEN parent.lft AND parent.rgt and node.company = '" + comp + "' and node.docstatus != 2 GROUP BY node.name ORDER BY node.lft";
	}
	
	return q;
}
