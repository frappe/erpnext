QUnit.test("test: quotation", function (assert) {
	assert.expect(12);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Quotation", [
				{customer: "Test Customer 1"},
				{items: [
					[
						{"item_code": "Test Product 1"},
						{"qty": 5}
					]]
				},
				{payment_terms_template: '_Test Payment Term Template UI'}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name == "Test Product 1", "Added Test Product 1");

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total === 500, String(cur_frm.doc.grand_total));
		},
		() => cur_frm.set_value("customer_address", "Test1-Billing"),
		() => cur_frm.set_value("shipping_address_name", "Test1-Warehouse"),
		() => cur_frm.set_value("contact_person", "Contact 1-Test Customer 1"),
		() => cur_frm.set_value("currency", "USD"),
		() => frappe.timeout(0.3),
		() => cur_frm.set_value("selling_price_list", "Test-Selling-USD"),
		() => frappe.timeout(0.5),
		() => cur_frm.doc.items[0].rate = 200,
		() => frappe.timeout(0.3),
		() => cur_frm.set_value("tc_name", "Test Term 1"),
		() => cur_frm.set_value("payment_schedule", []),
		() => frappe.timeout(0.5),
		() => cur_frm.save(),
		() => {
			// Check Address and Contact Info
			assert.ok(cur_frm.doc.address_display.includes("Billing Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.shipping_address.includes("Warehouse Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.contact_display == "Contact 1", "Contact info changed");

			// Check Currency
			assert.ok(cur_frm.doc.currency == "USD", "Currency Changed");
			assert.ok(cur_frm.doc.selling_price_list == "Test-Selling-USD", "Price List Changed");
			assert.ok(cur_frm.doc.items[0].rate == 200, "Price Changed Manually");
			assert.equal(cur_frm.doc.total, 1000, "New Total Calculated");

			// Check Terms and Condtions
			assert.ok(cur_frm.doc.tc_name == "Test Term 1", "Terms and Conditions Checked");

			assert.ok(cur_frm.doc.payment_terms_template, "Payment Terms Template is correct");
			assert.ok(cur_frm.doc.payment_schedule.length > 0, "Payment Term Schedule is not empty");

		},
		() => done()
	]);
});
