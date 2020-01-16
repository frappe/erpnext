QUnit.module('Stock');

QUnit.test("test material Transfer to manufacture", function(assert) {
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Stock Entry', [
				{purpose:'Material Transfer for Manufacture'},
				{from_warehouse:'Stores - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
				{to_warehouse:'Work In Progress - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 1},
					]
				]},
			]);
		},
		() => cur_frm.save(),
		() => frappe.click_button('Update Rate and Availability'),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			assert.ok(cur_frm.doc.total_outgoing_value==100, " Outgoing Value correct");
			assert.ok(cur_frm.doc.total_incoming_value==100, " Incoming Value correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

