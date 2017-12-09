QUnit.module('Stock');

QUnit.test("test item price", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Item Price', [
				{price_list:'Test-Selling-USD'},
				{item_code: 'Test Product 4'},
				{price_list_rate: 200}
			]);
		},
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.item_name == 'Test Product 4', "Item name correct");
			assert.ok(cur_frm.doc.price_list_rate == 200, "Price list rate correct");
		},
		() => frappe.timeout(0.3),
		() => done()
	]);
});