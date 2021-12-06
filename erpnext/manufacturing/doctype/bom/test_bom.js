QUnit.test("test: item", function (assert) {
	assert.expect(1);
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
				{company: "For Testing"},
				{operations: [
					[
						{operation: "Assemble CPU"},
						{time_in_mins: 60},
					],
					[
						{operation: "Assemble Keyboard"},
						{time_in_mins: 30},
					],
					[
						{operation: "Assemble Screen"},
						{time_in_mins: 30},
					]
				]},
				{scrap_items: [
					[
						{item_code: "Scrap item"}
					]
				]},
				{items: [
					[
						{item_code: "CPU"},
						{qty: 1}
					],
					[
						{item_code: "Keyboard"},
						{qty: 1}
					],
					[
						{item_code: "Screen"},
						{qty: 1}
					]
				]},
			]
		),
		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),

		() => {
			assert.ok(cur_frm.doc.operating_cost + cur_frm.doc.raw_material_cost -
			cur_frm.doc.scrap_material_cost == cur_frm.doc.total_cost, 'Total_Cost calculated correctly');
		},

		() => done()
	]);
});
