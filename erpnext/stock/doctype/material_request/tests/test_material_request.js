QUnit.module('Stock');

QUnit.test("test material request", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Material Request', [
				{items: [
					[
<<<<<<< da30a69ee753381fa9cab01c4d128ce236b4bdd3
						{'schedule_date':  frappe.datetime.add_days(frappe.datetime.nowdate(), 5)},
=======
						{'schedule_date': frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
>>>>>>> [UI Test] test added for Material Request
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

