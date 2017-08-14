QUnit.module('Buying');

QUnit.test("test: supplier quotation with item wise discount", function(assert){
	assert.expect(2);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Supplier Quotation', [
				{supplier: 'Test Supplier'},
				{company: 'Test Company'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"uom": 'Unit'},
						{"warehouse": 'All Warehouses - TC'},
						{'discount_percentage': 10},
					]
				]}
			]);
		},

		() => {
			assert.ok(cur_frm.doc.total == 900, "Total correct");
			assert.ok(cur_frm.doc.grand_total == 900, "Grand total correct");
		},

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});