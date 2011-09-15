//make tabs

pscript.onload_people = function() {
	make_customer_tab($i('crm_home'));
}

function make_customer_tab(parent) {	
	new wn.widgets.DocColumnView('Customers', parent, ['Customer Group', 'Customer', 'Contact'], {
		'Customer Group': { 
			show_fields : ['name'],
			create_fields : ['name'],
			search_fields : ['name'],
			next_col: 'Customer'
		},
		'Customer': { 
			show_fields : ['name', 'customer_name'],
			create_fields : ['name', 'customer_name'],
			search_fields : ['customer_name'],
			filter_by : ['Customer Group', 'customer_group'],
			next_col: 'Contact'
		},
		'Contact': { 
			show_fields : ['name', 'first_name', 'last_name'],
			create_fields : ['name','first_name', 'last_name'],
			search_fields : ['first_name', 'last_name'],
			conditions: ['is_customer=1'],
			filter_by : ['Customer', 'customer']
		},
	})
}


