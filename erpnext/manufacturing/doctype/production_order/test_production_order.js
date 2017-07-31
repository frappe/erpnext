QUnit.test("test: production order", function (assert) {
	assert.expect(2);
	let done = assert.async();
	let laptop_quantity = 5;
	let single_laptop_cost = 1340; // Calculated in workstation (time * per_hour_cost) for every item

	frappe.run_serially([
		// test production order
		() => frappe.set_route("List", "Production Order"),
		() => frappe.timeout(0.5),

		// Create a laptop production order
		() => frappe.new_doc("Production Order"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("production_item", "Laptop"),
		() => frappe.timeout(2),
		() => cur_frm.set_value("company", "Razer Blade"),
		() => frappe.timeout(2),
		() => cur_frm.set_value("qty", laptop_quantity),
		() => frappe.timeout(2),
		() => cur_frm.set_value("scrap_warehouse", "Laptop Scrap Warehouse - RB"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("wip_warehouse", "Work In Progress - RB"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("fg_warehouse", "Finished Goods - RB"),
		() => cur_frm.save(),
		() => frappe.timeout(1),

		() => {
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost, "Total and Planned Cost is equal");
			assert.equal(cur_frm.doc.planned_operating_cost, laptop_quantity*single_laptop_cost, "Total cost is calculated correctly "+cur_frm.doc.planned_operating_cost);
		},

		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),

		() => done()
	]);
});
