QUnit.module('Stock');

QUnit.test("test delivery note", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Delivery Note', [
				{customer:'Test Customer 1'},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 5},
					]
				]},
				{shipping_address_name: 'Test1-Shipping'},
				{contact_person: 'Contact 1-Test Customer 1'},
				{taxes_and_charges: 'TEST In State GST - FT'},
				{tc_name: 'Test Term 1'},
				{transporter_name:'TEST TRANSPORT'},
				{lr_no:'MH-04-FG 1111'}
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			assert.ok(cur_frm.doc.grand_total==590, " Grand Total correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

