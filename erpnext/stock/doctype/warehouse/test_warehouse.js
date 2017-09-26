QUnit.test("test: warehouse", function (assert) {
	assert.expect(0);
	let done = assert.async();

	frappe.run_serially([
		// test warehouse creation
		() => frappe.set_route("List", "Warehouse"),

		// Create a Laptop Scrap Warehouse
		() => frappe.tests.make(
			"Warehouse", [
				{warehouse_name: "Laptop Scrap Warehouse"},
				{company: "For Testing"}
			]
		),

		() => done()
	]);
});