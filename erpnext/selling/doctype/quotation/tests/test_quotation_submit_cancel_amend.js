QUnit.module('Quotation');

QUnit.test("test quotation submit cancel amend", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Quotation', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'delivery_date': frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
						{'qty': 5},
						{'item_code': 'Test Product 1'}
					]
				]},
				{customer_address: 'Test1-Billing'},
				{shipping_address_name: 'Test1-Shipping'},
				{contact_person: 'Contact 1-Test Customer 1'}
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			// get uom details
			assert.ok(cur_frm.doc.grand_total== 500, "Grand total correct ");

		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Close'),
		() => frappe.tests.click_button('Cancel'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Amend'),
		() => cur_frm.save(),
		() => done()
	]);
});
