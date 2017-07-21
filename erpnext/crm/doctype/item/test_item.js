QUnit.test("test: item", function (assert) {
	assert.expect(18);
	let done = assert.async();
	frappe.run_serially([
		// test item creation
		() => frappe.set_route("List", "Item"),

		// Create a keyboard item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Keyboard"},
				{item_group: "Products"},
				{is_stock_item: 1},
				{standard_rate: 1000},
				{opening_stock: 100}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Keyboard'),
				'Item Keyboard created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Keyboard'),
				'item_code for Keyboard set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Keyboard set correctly');
			assert.equal(cur_frm.doc.is_stock_item, 1,
				'is_stock_item for Keyboard set correctly');
			assert.equal(cur_frm.doc.standard_rate, 1000,
				'standard_rate for Keyboard set correctly');
			assert.equal(cur_frm.doc.opening_stock, 100,
				'opening_stock for Keyboard set correctly');
		},

		// Create a Screen item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Screen"},
				{item_group: "Products"},
				{is_stock_item: 1},
				{standard_rate: 1000},
				{opening_stock: 100}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Screen'),
				'Item Screen created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Screen'),
				'item_code for Screen set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Screen set correctly');
			assert.equal(cur_frm.doc.is_stock_item, 1,
				'is_stock_item for Screen set correctly');
			assert.equal(cur_frm.doc.standard_rate, 1000,
				'standard_rate for Screen set correctly');
			assert.equal(cur_frm.doc.opening_stock, 100,
				'opening_stock for Screen set correctly');
		},

		// Create a CPU item
		() => frappe.tests.make(
			"Item", [
				{item_code: "CPU"},
				{item_group: "Products"},
				{is_stock_item: 1},
				{standard_rate: 1000},
				{opening_stock: 100}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('CPU'),
				'Item CPU created correctly');
			assert.ok(cur_frm.doc.item_code.includes('CPU'),
				'item_code for CPU set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for CPU set correctly');
			assert.equal(cur_frm.doc.is_stock_item, 1,
				'is_stock_item for CPU set correctly');
			assert.equal(cur_frm.doc.standard_rate, 1000,
				'standard_rate for CPU set correctly');
			assert.equal(cur_frm.doc.opening_stock, 100,
				'opening_stock for CPU set correctly');
		},

		() => done()
	]);
});
