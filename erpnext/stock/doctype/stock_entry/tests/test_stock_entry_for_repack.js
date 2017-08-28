QUnit.module('Stock');

QUnit.test("test repack", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Stock Entry', [
				{purpose:'Repack'},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 1},
						{'s_warehouse':'Stores - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
					],
					[
						{'item_code': 'Test Product 2'},
						{'qty': 1},
						{'s_warehouse':'Stores - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
					],
					[
						{'item_code': 'Test Product 3'},
						{'qty': 1},
						{'t_warehouse':'Work In Progress - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
					],
				]},
			]);
		},
		() => cur_frm.save(),
		() => frappe.click_button('Update Rate and Availability'),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.total_outgoing_value==250, " Outgoing Value correct");
			assert.ok(cur_frm.doc.total_incoming_value==250, " Incoming Value correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

