QUnit.module('Stock');

QUnit.test("test material request for transfer", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Material Request', [
				{material_request_type:'Manufacture'},
				{items: [
					[
						{'schedule_date':  frappe.datetime.add_days(frappe.datetime.nowdate(), 5)},
						{'qty': 5},
						{'item_code': 'Test Product 1'},
					]
				]},
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

