QUnit.module('Buying');

QUnit.test("test: purchase order with taxes and charges", function(assert) {
	assert.expect(3);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{buying_price_list: 'Test-Buying-USD'},
				{currency: 'USD'},
				{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"uom": 'Unit'},
						{"rate": 500 },
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]},

				{taxes_and_charges: 'TEST In State GST - FT'}
			]);
		},

		() => {
			// Check taxes and calculate grand total
			assert.ok(cur_frm.doc.taxes[1].account_head=='SGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')), "Account Head abbr correct");
			assert.ok(cur_frm.doc.total_taxes_and_charges == 225, "Taxes and charges correct");
			assert.ok(cur_frm.doc.grand_total == 2725, "Grand total correct");
		},

		() => frappe.timeout(0.3),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});
