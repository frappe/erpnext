QUnit.test("test: production order", function (assert) {
	assert.expect(25);
	let done = assert.async();
	let laptop_quantity = 5;
	let items = ["CPU", "Keyboard", "Screen"];
	let operation_items = ["CPU", "Keyboard", "Screen"];
	let click_make = () => {
		let element = $(`.btn-primary:contains("Make"):visible`);
		if(!element.length) {
			throw `did not find any button containing 'Make'`;
		}
		element.click();
		return frappe.timeout(1);
	};

	frappe.run_serially([
		// test production order
		() => frappe.set_route("List", "Production Order", "List"),
		() => frappe.timeout(3),

		// Create a laptop production order
		() => {
			return frappe.tests.make('Production Order', [
				{production_item: 'Laptop'},
				{company: 'For Testing'},
				{qty: laptop_quantity},
				{scrap_warehouse: "Laptop Scrap Warehouse - FT"},
				{wip_warehouse: "Work In Progress - FT"},
				{fg_warehouse: "Finished Goods - FT"}
			]);
		},
		() => frappe.timeout(3),
		() => {
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost,
				"Total and Planned Cost is equal");
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost,
				"Total and Planned Cost is equal");

			items.forEach(function(item, index) {
				assert.equal(item, cur_frm.doc.required_items[index].item_code, `Required item ${item} added`);
				assert.equal("Stores - FT", cur_frm.doc.required_items[index].source_warehouse, `Item ${item} warhouse verified`);
				assert.equal("5", cur_frm.doc.required_items[index].required_qty, `Item ${item} quantity verified`);
			});

			operation_items.forEach(function(operation_item, index) {
				assert.equal(`Assemble ${operation_item}`, cur_frm.doc.operations[index].operation,
					`Operation ${operation_item} added`);
				assert.equal(`${operation_item} assembly workstation`, cur_frm.doc.operations[index].workstation,
					`Workstation ${operation_item} linked`);
			});
		},

		// Submit the production order
		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(2.5),

		// Confirm the production order timesheet, save and submit it
		() => frappe.click_link("TS-00"),
		() => frappe.timeout(1),
		() => frappe.click_button("Submit"),
		() => frappe.timeout(1),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(2.5),

		// Start the production order process
		() => frappe.set_route("List", "Production Order", "List"),
		() => frappe.timeout(2),
		() => frappe.click_link("Laptop"),
		() => frappe.timeout(1),
		() => frappe.click_button("Start"),
		() => frappe.timeout(0.5),
		() => click_make(),
		() => frappe.timeout(1),
		() => frappe.click_button("Save"),
		() => frappe.timeout(0.5),

		() => {
			assert.equal(cur_frm.doc.total_outgoing_value, cur_frm.doc.total_incoming_value,
				"Total incoming and outgoing cost is equal");
			assert.equal(cur_frm.doc.total_outgoing_value, "99000",
				"Outgoing cost is correct"); // Price of each item x5
		},
		// Submit for production
		() => frappe.click_button("Submit"),
		() => frappe.timeout(0.5),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(0.5),

		// Finish the production order by sending for manufacturing
		() => frappe.set_route("List", "Production Order"),
		() => frappe.timeout(1),
		() => frappe.click_link("Laptop"),
		() => frappe.timeout(1),

		() => {
			assert.ok(frappe.tests.is_visible("5 items in progress", 'p'), "Production order initiated");
			assert.ok(frappe.tests.is_visible("Finish"), "Finish button visible");
		},

		() => frappe.click_button("Finish"),
		() => frappe.timeout(0.5),
		() => click_make(),
		() => {
			assert.equal(cur_frm.doc.total_incoming_value, "105700",
				"Incoming cost is correct "+cur_frm.doc.total_incoming_value); // Price of each item x5, values are in INR
			assert.equal(cur_frm.doc.total_outgoing_value, "99000",
				"Outgoing cost is correct"); // Price of each item x5, values are in INR
			assert.equal(cur_frm.doc.total_incoming_value - cur_frm.doc.total_outgoing_value, cur_frm.doc.value_difference,
				"Value difference is correct"); // Price of each item x5, values are in INR
		},
		() => frappe.click_button("Save"),
		() => frappe.timeout(1),
		() => frappe.click_button("Submit"),
		() => frappe.timeout(1),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(1),

		// Manufacturing finished
		() => frappe.set_route("List", "Production Order", "List"),
		() => frappe.timeout(1),
		() => frappe.click_link("Laptop"),
		() => frappe.timeout(1),

		() => assert.ok(frappe.tests.is_visible("5 items produced", 'p'), "Production order completed"),

		() => done()
	]);
});
