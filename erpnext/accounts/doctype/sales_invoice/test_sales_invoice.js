QUnit.module('Sales Invoice');

QUnit.test("test sales Invoice", function(assert) {
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Sales Invoice', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'qty': 5},
						{'item_code': 'Test Product 1'},
					]
				]},
				{update_stock:1},
				{customer_address: 'Test1-Billing'},
				{shipping_address_name: 'Test1-Shipping'},
				{contact_person: 'Contact 1-Test Customer 1'},
				{taxes_and_charges: 'TEST In State GST'},
				{tc_name: 'Test Term 1'},
				{terms: 'This is Test'}
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			// get tax details
			assert.ok(cur_frm.doc.taxes_and_charges=='TEST In State GST', "Tax details correct");
			// get tax account head details
			assert.ok(cur_frm.doc.taxes[0].account_head=='CGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')), " Account Head abbr correct");
			// grand_total Calculated
			assert.ok(cur_frm.doc.grand_total==590, "Grad Total correct");

		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});

QUnit.test("test sales Invoice currency is read only when stale currency not allowed", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		// change currency exchange settings
		() => frappe.set_route('Form', 'Currency Exchange Settings', 'Currency Exchange Settings'),
		() => {
			if(cur_frm.doc.allow_stale === '1'){
				frappe.click_check('Allow Stale Exchange Rates');
			}
		},
		// back to sales invoice
		() => frappe.set_route('Form', 'Sales Invoice', 'New Sales Invoice 1'),
		() => {
			return frappe.tests.make('Sales Invoice', [
				{customer: 'AUD Customer'},
			]);
		},
		frappe.timeout(3),
		() => {
			assert.ok(frappe.tests.control_field_is_read_only('conversion_rate'));
		},
		// clean up after test
		() => frappe.set_route('Form', 'Currency Exchange Settings', 'Currency Exchange Settings'),
		() => {
			if(cur_frm.doc.allow_stale === '0'){
				frappe.click_check('Allow Stale Exchange Rates');
			}
		},
		() => done()
	]);
});