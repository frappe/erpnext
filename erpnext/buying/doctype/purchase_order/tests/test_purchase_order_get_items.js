QUnit.module('Buying');

QUnit.test("test: purchase order with get items", function(assert) {
	assert.expect(4);
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
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]}
			]);
		},

		() => {
			assert.ok(cur_frm.doc.supplier_name == 'Test Supplier', "Supplier name correct");
		},

		() => frappe.timeout(0.3),
		() => frappe.click_button('Get items from'),
		() => frappe.timeout(0.3),

		() => frappe.click_link('Product Bundle'),
		() => frappe.timeout(0.5),

		() => cur_dialog.set_value('product_bundle', 'Computer'),
		() => frappe.click_button('Get Items'),
		() => frappe.timeout(1),

		// Check if items are fetched from Product Bundle
		() => {
			assert.ok(cur_frm.doc.items[1].item_name == 'CPU', "Product bundle item 1 correct");
			assert.ok(cur_frm.doc.items[2].item_name == 'Screen', "Product bundle item 2 correct");
			assert.ok(cur_frm.doc.items[3].item_name == 'Keyboard', "Product bundle item 3 correct");
		},

		() => cur_frm.doc.items[1].warehouse = 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company")),
		() => cur_frm.doc.items[2].warehouse = 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company")),
		() => cur_frm.doc.items[3].warehouse = 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company")),

		() => cur_frm.save(),
		() => frappe.timeout(1),

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),

		() => done()
	]);
});
