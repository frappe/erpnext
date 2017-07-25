QUnit.test("test: production order", function (assert) {
	assert.expect(2);
	let done = assert.async();
	let laptop_quantity = 10;
	let single_laptop_cost = 1340; // Calculated in workstation (time * per_hour_cost) for every item
	let company_initials = "";
	let get_company_initials = () => {
		return $(".list-id").text().match(/\b(\w)/g).join(''); // using regex to retrive initials from company name
	};

	frappe.run_serially([
		// retrive company name (to use in warehouse selection)
		() => frappe.set_route("List", "Company"),
		() => frappe.timeout(0.5),
		() => company_initials = get_company_initials(),

		// test production order
		() => frappe.set_route("List", "Production Order"),

		// Create a keyboard workstation
		() => frappe.tests.make(
			"Production Order", [
				{production_item: "Laptop"},
				{qty: laptop_quantity},
				{wip_warehouse: "Work in Progress Warehouse - "+company_initials},
				{fg_warehouse: "Finished Laptop Warehouse - "+company_initials},
				{scrap_warehouse: "Laptop Scrap Warehouse - "+company_initials}
			]
		),

		// () => cur_frm.savesubmit(),
		// () => frappe.timeout(1),
		// () => $(`button.btn.btn-primary:contains('Yes')`).click()
		// () => frappe.timeout(1),

		() => {
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost, "Total and Planned Cost is equal");
			assert.equal(cur_frm.doc.planned_operating_cost, laptop_quantity*single_laptop_cost, "Total cost is calculated correctly");
		},

		() => done()
	]);
});
