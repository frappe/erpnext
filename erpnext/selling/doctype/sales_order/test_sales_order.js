$.extend(frappe.test_data, {
	"Item": {
		"Test Product 4": [
			{item_code: "Test Product 4"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{has_batch_no: 1},
			{uoms:
				[
					[
						{uom:"Unit"},
						{conversion_factor: 10},
					]
				]
			},
			{taxes:
				[
					[
						{tax_type:"SGST - "+frappe.get_abbr(frappe.defaults.get_default("Company"))},
						{tax_rate: 0},
					]
				]},
			{create_new_batch: 1},
			{has_serial_no: 1},
			{standard_rate: 100},
			{opening_stock: 100},
		]
	}
});

QUnit.module('Sales Order');

QUnit.test('fixtures multi uom and tax' , assert => {
	// create all fixtures first
	assert.expect(0);
	let done = assert.async();
	let tasks = [];
	Object.keys(frappe.test_data).forEach(function(doctype) {
		tasks.push(function() { return frappe.tests.setup_doctype(doctype); });
	});
	frappe.run_serially(tasks).then(() => done());
});


QUnit.test("test sales order", function(assert) {
	assert.expect(6);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Sales Order', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'delivery_date': frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
						{'qty': 5},
						{'item_code': 'Test Product 1'},
					],
					[
						{'delivery_date': frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
						{'qty': 5},
						{'item_code': 'Test Product 4'},
						{'uom': 'unit'},
						{'margin_type': 'Percentage'},
						{'discount_percentage': 10},
					]
				]},
				{customer_address: 'Test1-Billing'},
				{shipping_address_name: 'Test1-Shipping'},
				{contact_person: 'Contact 1-Test Customer 1'},
				{taxes_and_charges: 'TEST In State GST'},
				{tc_name: 'Test Term 1'},
				{terms: 'This is Test'}
			]);
		},
		() => { return frappe.tests.set_form_values(cur_frm, [
					{selling_price_list:'Test-Selling-USD'},
					{currency: 'USD'},
					{apply_discount_on:'Grand Total'},
					{additional_discount_percentage:10}
				]);
			},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			// get tax details
			assert.ok(cur_frm.doc.taxes_and_charges=='TEST In State GST', "Tax details correct");
			// get tax account head details
			assert.ok(cur_frm.doc.taxes[0].account_head=='CGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')), " Account Head abbr correct");
			// calculate totals
			assert.ok(cur_frm.doc.grand_total== 4504.05, "grand total correct");
			},
		() => cur_frm.print_doc(),
		() => frappe.timeout(1),
		() => {
			assert.ok($('.btn-print-print').is(':visible'), "Print Format Available");
			assert.ok($(".section-break+ .section-break .column-break:nth-child(1) .data-field:nth-child(1) .value").text().includes("Billing Street 1"), "Print Preview Works As Expected");
		},
		() => cur_frm.print_doc(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

