QUnit.test("test: item", function (assert) {
	assert.expect(27);
	let done = assert.async();
	let keyboard_cost  = 800;
	let screen_cost  = 4000;
	let CPU_cost  = 15000;
	let scrap_cost = 100;
	let no_of_items_to_stock = 100;
	let is_stock_item = 1;
	frappe.run_serially([
		// test item creation
		() => frappe.set_route("List", "Item"),

		// Create a keyboard item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Keyboard"},
				{item_group: "Products"},
				{is_stock_item: is_stock_item},
				{standard_rate: keyboard_cost},
				{opening_stock: no_of_items_to_stock}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Keyboard'),
				'Item Keyboard created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Keyboard'),
				'item_code for Keyboard set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Keyboard set correctly');
			assert.equal(cur_frm.doc.is_stock_item, is_stock_item,
				'is_stock_item for Keyboard set correctly');
			assert.equal(cur_frm.doc.standard_rate, keyboard_cost,
				'standard_rate for Keyboard set correctly');
			assert.equal(cur_frm.doc.opening_stock, no_of_items_to_stock,
				'opening_stock for Keyboard set correctly');
		},

		// Create a Screen item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Screen"},
				{item_group: "Products"},
				{is_stock_item: is_stock_item},
				{standard_rate: screen_cost},
				{opening_stock: no_of_items_to_stock}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Screen'),
				'Item Screen created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Screen'),
				'item_code for Screen set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Screen set correctly');
			assert.equal(cur_frm.doc.is_stock_item, is_stock_item,
				'is_stock_item for Screen set correctly');
			assert.equal(cur_frm.doc.standard_rate, screen_cost,
				'standard_rate for Screen set correctly');
			assert.equal(cur_frm.doc.opening_stock, no_of_items_to_stock,
				'opening_stock for Screen set correctly');
		},

		// Create a CPU item
		() => frappe.tests.make(
			"Item", [
				{item_code: "CPU"},
				{item_group: "Products"},
				{is_stock_item: is_stock_item},
				{standard_rate: CPU_cost},
				{opening_stock: no_of_items_to_stock}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('CPU'),
				'Item CPU created correctly');
			assert.ok(cur_frm.doc.item_code.includes('CPU'),
				'item_code for CPU set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for CPU set correctly');
			assert.equal(cur_frm.doc.is_stock_item, is_stock_item,
				'is_stock_item for CPU set correctly');
			assert.equal(cur_frm.doc.standard_rate, CPU_cost,
				'standard_rate for CPU set correctly');
			assert.equal(cur_frm.doc.opening_stock, no_of_items_to_stock,
				'opening_stock for CPU set correctly');
		},

		// Create a laptop item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Laptop"},
				{item_group: "Products"}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Laptop'),
				'Item Laptop created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Laptop'),
				'item_code for Laptop set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Laptop set correctly');
		},

		// Create a scrap item
		() => frappe.tests.make(
			"Item", [
				{item_code: "Scrap item"},
				{item_group: "Products"},
				{is_stock_item: is_stock_item},
				{standard_rate: scrap_cost},
				{opening_stock: no_of_items_to_stock}
			]
		),
		() => {
			assert.ok(cur_frm.doc.item_name.includes('Scrap item'),
				'Item Scrap item created correctly');
			assert.ok(cur_frm.doc.item_code.includes('Scrap item'),
				'item_code for Scrap item set correctly');
			assert.ok(cur_frm.doc.item_group.includes('Products'),
				'item_group for Scrap item set correctly');
			assert.equal(cur_frm.doc.is_stock_item, is_stock_item,
				'is_stock_item for Scrap item set correctly');
			assert.equal(cur_frm.doc.standard_rate, scrap_cost,
				'standard_rate for Scrap item set correctly');
			assert.equal(cur_frm.doc.opening_stock, no_of_items_to_stock,
				'opening_stock for Scrap item set correctly');
		},

		() => done()
	]);
});
