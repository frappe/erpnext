QUnit.module('Buying');

QUnit.test("test: purchase order with discount on grand total", function(assert) {
	assert.expect(4);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{buying_price_list: 'Test-Buying-EUR'},
				{currency: 'EUR'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"uom": 'Unit'},
						{"rate": 500 },
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]},
				{apply_discount_on: 'Grand Total'},
				{additional_discount_percentage: 10}
			]);
		},

		() => frappe.timeout(1),

		() => {
			assert.ok(cur_frm.doc.supplier_name == 'Test Supplier', "Supplier name correct");
			assert.ok(cur_frm.doc.items[0].rate == 500, "Rate correct");
			// Calculate total
			assert.ok(cur_frm.doc.total == 2500, "Total correct");
			// Calculate grand total after discount
			assert.ok(cur_frm.doc.grand_total == 2250, "Grand total correct");
		},

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),

		() => done()
	]);
});
