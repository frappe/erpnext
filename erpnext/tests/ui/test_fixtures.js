$.extend(frappe.test_data, {
	'Customer': {
		'Test Customer 1': [
			{customer_name: 'Test Customer 1'},
		],
		'Test Customer 2': [
			{customer_name: 'Test Customer 2'}
		],
		'Test Customer 3': [
			{customer_name: 'Test Customer 3'}
		],
	},
	'Item': {
		'Test Product 1': [
			{item_code: 'Test Product 1'},
			{item_group: 'Products'},
			{is_stock_item: 1},
			{standard_rate: 100},
			{opening_stock: 100},
		],
		'Test Product 2': [
			{item_code: 'Test Product 2'},
			{item_group: 'Products'},
			{is_stock_item: 1},
			{standard_rate: 150},
			{opening_stock: 200},
		],
		'Test Product 3': [
			{item_code: 'Test Product 3'},
			{item_group: 'Products'},
			{is_stock_item: 1},
			{standard_rate: 250},
			{opening_stock: 100},
		],
		'Test Service 1': [
			{item_code: 'Test Service 1'},
			{item_group: 'Services'},
			{is_stock_item: 0},
			{standard_rate: 200}
		],
		'Test Service 2': [
			{item_code: 'Test Service 2'},
			{item_group: 'Services'},
			{is_stock_item: 0},
			{standard_rate: 300}
		]
	},
	'Lead':{
		'LEAD-00001': [
			{lead_name: 'Test Lead 1'}
		],
		'LEAD-00002': [
			{lead_name: 'Test Lead 2'}
		],
		'LEAD-00003': [
			{lead_name: 'Test Lead 3'}
		]
	}
});
