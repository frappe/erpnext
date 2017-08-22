QUnit.module('Buying');

QUnit.test("test: purchase order receipt", function(assert) {
	assert.expect(5);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{buying_price_list: 'Test-Buying-USD'},
				{currency: 'USD'},
				{items: [
					[
						{"item_code": 'Test Product 1'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 5},
						{"uom": 'Unit'},
						{"rate": 100},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]},
			]);
		},

		() => {

			// Check supplier and item details
			assert.ok(cur_frm.doc.supplier_name == 'Test Supplier', "Supplier name correct");
			assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 1', "Item name correct");
			assert.ok(cur_frm.doc.items[0].description == 'Test Product 1', "Description correct");
			assert.ok(cur_frm.doc.items[0].qty == 5, "Quantity correct");

		},

		() => frappe.timeout(1),

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),

		() => frappe.timeout(1.5),
		() => frappe.click_button('Close'),
		() => frappe.timeout(0.3),

		// Make Purchase Receipt
		() => frappe.click_button('Make'),
		() => frappe.timeout(0.3),

		() => frappe.click_link('Receipt'),
		() => frappe.timeout(2),

		() => cur_frm.save(),

		// Save and submit Purchase Receipt
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),

		// View Purchase order in Stock Ledger
		() => frappe.click_button('View'),
		() => frappe.timeout(0.3),

		() => frappe.click_link('Stock Ledger'),
		() => frappe.timeout(2),
		() => {
			assert.ok($('div.slick-cell.l2.r2 > a').text().includes('Test Product 1')
				&& $('div.slick-cell.l9.r9 > div').text().includes(5), "Stock ledger entry correct");
		},
		() => done()
	]);
});
