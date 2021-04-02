$.extend(frappe.test_data, {
	// "Fiscal Year": {
	// 	"2017-18": [
	// 		{"year": "2017-18"},
	// 		{"year_start_date": "2017-04-01"},
	// 		{"year_end_date": "2018-03-31"},
	// 	]
	// },
	"Customer": {
		"Test Customer 1": [
			{customer_name: "Test Customer 1"}
		],
		"Test Customer 2": [
			{customer_name: "Test Customer 2"}
		],
		"Test Customer 3": [
			{customer_name: "Test Customer 3"}
		],
	},
	"Item": {
		"Test Product 1": [
			{item_code: "Test Product 1"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 100},
			{opening_stock: 100},
		],
		"Test Product 2": [
			{item_code: "Test Product 2"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 150},
			{opening_stock: 200},
		],
		"Test Product 3": [
			{item_code: "Test Product 3"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 250},
			{opening_stock: 100},
			{stock_uom:'Kg'}
		],
		"Test Service 1": [
			{item_code: "Test Service 1"},
			{item_group: "Services"},
			{is_stock_item: 0},
			{standard_rate: 200}
		],
		"Test Service 2": [
			{item_code: "Test Service 2"},
			{item_group: "Services"},
			{is_stock_item: 0},
			{standard_rate: 300}
		]
	},
	"Lead": {
		"LEAD-00001": [
			{lead_name: "Test Lead 1"}
		],
		"LEAD-00002": [
			{lead_name: "Test Lead 2"}
		],
		"LEAD-00003": [
			{lead_name: "Test Lead 3"}
		]
	},
	"Address": {
		"Test1-Billing": [
			{address_title:"Test1"},
			{address_type: "Billing"},
			{address_line1: "Billing Street 1"},
			{city: "Billing City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test1-Shipping": [
			{address_title:"Test1"},
			{address_type: "Shipping"},
			{address_line1: "Shipping Street 1"},
			{city: "Shipping City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test1-Warehouse": [
			{address_title:"Test1"},
			{address_type: "Warehouse"},
			{address_line1: "Warehouse Street 1"},
			{city: "Warehouse City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test2-Billing": [
			{address_title:"Test2"},
			{address_type: "Billing"},
			{address_line1: "Billing Street 2"},
			{city: "Billing City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Test2-Shipping": [
			{address_title:"Test2"},
			{address_type: "Shipping"},
			{address_line1: "Shipping Street 2"},
			{city: "Shipping City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Test2-Warehouse": [
			{address_title:"Test2"},
			{address_type: "Warehouse"},
			{address_line1: "Warehouse Street 2"},
			{city: "Warehouse City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		]
	},
	"Contact": {
		"Contact 1-Test Customer 1": [
			{first_name: "Contact 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Contact 2-Test Customer 1": [
			{first_name: "Contact 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Contact 1-Test Customer 2": [
			{first_name: "Contact 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Contact 2-Test Customer 2": [
			{first_name: "Contact 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
	},
	"Price List": {
		"Test-Buying-USD": [
			{price_list_name: "Test-Buying-USD"},
			{currency: "USD"},
			{buying: "1"}
		],
		"Test-Buying-EUR": [
			{price_list_name: "Test-Buying-EUR"},
			{currency: "EUR"},
			{buying: "1"}
		],
		"Test-Selling-USD": [
			{price_list_name: "Test-Selling-USD"},
			{currency: "USD"},
			{selling: "1"}
		],
		"Test-Selling-EUR": [
			{price_list_name: "Test-Selling-EUR"},
			{currency: "EUR"},
			{selling: "1"}
		],
	},
	"Terms and Conditions": {
		"Test Term 1": [
			{title: "Test Term 1"}
		],
		"Test Term 2": [
			{title: "Test Term 2"}
		]
	},
	"Item Price": {
		"ITEM-PRICE-00001": [
			{item_code: 'Test Product 1'},
			{price_list: '_Test Price List'},
			{price_list_rate: 100}
		],
		"ITEM-PRICE-00002": [
			{item_code: 'Test Product 2'},
			{price_list: '_Test Price List'},
			{price_list_rate: 200}
		]
	},
	"Payment Term": {
		"_Test Payment Term": [
			{payment_term_name: '_Test Payment Term'},
			{due_date_based_on: 'Day(s) after invoice date'},
			{invoice_portion: 100},
			{credit_days: 0}
		]
	},
	"Payment Terms Template": {
		"_Test Payment Term Template UI": [
			{template_name: "_Test Payment Term Template UI"},
			{terms: [
				[
					{payment_term: '_Test Payment Term'},
					{invoice_portion: 100}
				]
			]}
		]
	}
});


// this is a script that creates all fixtures
// called as a test
QUnit.module('fixture');

QUnit.test('Make fixtures', assert => {
	// create all fixtures first
	assert.expect(0);
	let done = assert.async();
	let tasks = [];
	Object.keys(frappe.test_data).forEach(function(doctype) {
		tasks.push(function() {
			return frappe.tests.setup_doctype(doctype, frappe.test_data[doctype]);
		});
	});
	frappe.run_serially(tasks).then(() => done());
});
