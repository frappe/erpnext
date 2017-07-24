QUnit.test("test: item", function (assert) {
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		// test item creation
		() => frappe.set_route("List", "Item"),

		// Create a BOM for a laptop
		() => frappe.tests.make(
			"BOM", [
				{item: "Laptop"},
				{quantity: 1},
				{with_operations: 1},
				{operations: [
					[
						{operation: "CPU OP"},
						{time_in_mins: 480},
					]
				]},
				{operations: [
					[
						{operation: "Screen OP"},
						{time_in_mins: 480},
					]
				]},
				{operations: [
					[
						{operation: "Keyboard OP"},
						{time_in_mins: 480},
					]
				]},
				{scrap_items: [
					[
						{item_code: "Scrap item"}
					]
				]},
				{items: [
					[
						{item_code: "CPU"}
					]
				]},
				{items: [
					[
						{item_code: "Screen"}
					]
				]},
				{items: [
					[
						{item_code: "Keyboard"}
					]
				]}
			]
		),
		// () => {
		// 	assert.ok(cur_frm.doc.item_name.includes('Keyboard'),
		// 		'Item Keyboard created correctly');
		// 	assert.ok(cur_frm.doc.item_code.includes('Keyboard'),
		// 		'item_code for Keyboard set correctly');
		// 	assert.ok(cur_frm.doc.item_group.includes('Products'),
		// 		'item_group for Keyboard set correctly');
		// 	assert.equal(cur_frm.doc.is_stock_item, 1,
		// 		'is_stock_item for Keyboard set correctly');
		// 	assert.equal(cur_frm.doc.standard_rate, 1000,
		// 		'standard_rate for Keyboard set correctly');
		// 	assert.equal(cur_frm.doc.opening_stock, 100,
		// 		'opening_stock for Keyboard set correctly');
		// },

		() => done()
	]);
});
