QUnit.module('Stock');

QUnit.test("test material request", function(assert) {
	assert.expect(5);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Material Request', [
				{items: [
					[
						{'schedule_date':  frappe.datetime.add_days(frappe.datetime.nowdate(), 5)},
						{'qty': 5},
						{'item_code': 'Test Product 1'},
					],
					[
						{'schedule_date':  frappe.datetime.add_days(frappe.datetime.nowdate(), 6)},
						{'qty': 2},
						{'item_code': 'Test Product 2'},
					]
				]},
			]);
		},
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.schedule_date == frappe.datetime.add_days(frappe.datetime.now_date(), 5), "Schedule Date correct");

			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			assert.ok(cur_frm.doc.items[0].schedule_date == frappe.datetime.add_days(frappe.datetime.now_date(), 5), "Schedule Date correct");

			assert.ok(cur_frm.doc.items[1].item_name=='Test Product 2', "Item name correct");
			assert.ok(cur_frm.doc.items[1].schedule_date == frappe.datetime.add_days(frappe.datetime.now_date(), 6), "Schedule Date correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});
