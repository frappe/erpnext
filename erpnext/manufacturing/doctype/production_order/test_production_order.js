QUnit.test("test: production order", function (assert) {
	assert.expect(25);
	let done = assert.async();
	let laptop_quantity = 5;
	let required_item_code = (i) => {
		return $(`div:nth-child(4) > div.section-body > div > form > div > div > div > div.grid-body\
			> div.rows > div:nth-child(${i}) > div > div:nth-child(2) > div.static-area.ellipsis > a:visible`).text();
	};
	let required_source_warehouse = (i) => {
		return $(`div:nth-child(4) > div.section-body > div > form > div > div > div > div.grid-body\
			> div.rows > div:nth-child(${i}) > div > div:nth-child(3) > div.static-area.ellipsis > a:visible`).text();
	};
	let required_item_quantity = (i) => {
		return $(`div:nth-child(4) > div.section-body > div > form > div > div > div > div.grid-body\
			> div.rows > div:nth-child(${i}) > div > div:nth-child(4) > div.static-area.ellipsis > div:visible`).text();
	};
	let operation = (i) => {
		return $(`div:nth-child(6) > div.section-body > div > form > div > div > div > div.grid-body\
			> div.rows > div:nth-child(${i}) > div > div.col.grid-static-col.col-xs-3.bold > div.static-area.ellipsis > a:visible`).text();
	};
	let operation_workstaion = (i) => {
		return $(`div:nth-child(6) > div.section-body > div > form > div > div > div > div.grid-body\
			div:nth-child(${i}) > div > div:nth-child(4) > div.static-area.ellipsis > a:visible`).text();
	};
	let items = ["Screen", "CPU", "Keyboard"];
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
		() => frappe.timeout(2),

		() => {
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost, "Total and Planned Cost is equal");
			assert.equal(cur_frm.doc.planned_operating_cost, cur_frm.doc.total_operating_cost, "Total and Planned Cost is equal");

			items.forEach(function(item, index) {
				assert.equal(item, required_item_code(index+1), `Required item ${item} added`);
				assert.equal("Stores - RB", required_source_warehouse(1), `Item ${item} warhouse verified`);
				assert.equal("5", required_item_quantity(1), `Item ${item} quantity verified`);
			});

			operation_items.forEach(function(operation_item, index) {
				assert.equal(`Assemble ${operation_item}`, operation(index+1), `Operation ${operation_item} added`);
				assert.equal(`${operation_item} assembly workstation`, operation_workstaion(index+1), `Workstation ${operation_item} linked`);
			});
		},

		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),

		() => frappe.click_link("TS-000"),
		() => frappe.timeout(1),
		() => frappe.click_button("Save"),
		() => frappe.timeout(1),
		() => frappe.click_button("Submit"),
		() => frappe.timeout(1),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(2),

		() => frappe.set_route("List", "Production Order"),
		() => frappe.timeout(2),
		() => frappe.set_route("List", "Production Order"),
		() => frappe.timeout(2),
		() => frappe.click_link("Laptop"),
		() => frappe.timeout(1),

		() => frappe.click_button("Start"),
		() => frappe.timeout(0.5),
		() => click_make(),
		() => frappe.click_button("Save"),
		() => frappe.timeout(0.5),

		() => {
			assert.equal(cur_frm.doc.total_outgoing_value, cur_frm.doc.total_incoming_value, "Total incoming and outgoing cost is equal");
			assert.equal(cur_frm.doc.total_outgoing_value, "99000", "Outgoing cost is correct"); // Price of each item x5
		},

		() => frappe.click_button("Submit"),
		() => frappe.timeout(0.5),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(0.5),

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
			assert.equal(cur_frm.doc.total_incoming_value, "105700", "Incoming cost is correct"); // Price of each item x5
			assert.equal(cur_frm.doc.total_outgoing_value, "99000", "Outgoing cost is correct"); // Price of each item x5
			assert.equal(cur_frm.doc.total_incoming_value - cur_frm.doc.total_outgoing_value, cur_frm.doc.value_difference, "Value difference is correct"); // Price of each item x5
		},
		() => frappe.click_button("Save"),
		() => frappe.timeout(1),
		() => frappe.click_button("Submit"),
		() => frappe.timeout(1),
		() => frappe.click_button("Yes"),
		() => frappe.timeout(1),

		() => frappe.set_route("List", "Production Order"),
		() => frappe.timeout(1),
		() => frappe.click_link("Laptop"),
		() => frappe.timeout(1),

		() => assert.ok(frappe.tests.is_visible("5 items produced", 'p'), "Production order completed"),

		() => done()
	]);
});