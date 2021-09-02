QUnit.module('Price List');

QUnit.test("test price list with uom dependancy", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([

		() => frappe.set_route('Form', 'Price List', 'Standard Buying'),
		() => {
			cur_frm.set_value('price_not_uom_dependent','1');
			frappe.timeout(1);
		},
		() => cur_frm.save(),

		() => frappe.timeout(1),

		() => {
			return frappe.tests.make('Item Price', [
				{price_list:'Standard Buying'},
				{item_code: 'Test Product 3'},
				{price_list_rate: 200}
			]);
		},

		() => cur_frm.save(),

		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{currency: 'INR'},
				{buying_price_list: 'Standard Buying'},
				{items: [
					[
						{"item_code": 'Test Product 3'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 2)},
						{"uom": 'Nos'},
						{"conversion_factor": 3}
					]
				]},

			]);
		},

		() => cur_frm.save(),
		() => frappe.timeout(0.3),

		() => {
			assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 3', "Item code correct");
			assert.ok(cur_frm.doc.items[0].price_list_rate == 200, "Price list rate correct");
		},

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),

		() => done()
	]);
});
