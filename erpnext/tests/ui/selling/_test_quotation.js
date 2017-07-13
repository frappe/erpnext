QUnit.test("test: quotation", function (assert) {
	assert.expect(18);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.tests.setup_doctype("Customer"),
		() => frappe.tests.setup_doctype("Item"),
		() => frappe.tests.setup_doctype("Address"),
		() => frappe.tests.setup_doctype("Contact"),
		() => frappe.tests.setup_doctype("Price List"),
		() => frappe.tests.setup_doctype("Terms and Conditions"),
		() => frappe.tests.setup_doctype("Sales Taxes and Charges Template"),
		() => {
			return frappe.tests.make("Quotation", [{
				customer: "Test Customer 1"
			},
			{
				items: [
					[{
						"item_code": "Test Product 1"
					},
					{
						"qty": 5
					}
					]
				]
			}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name == "Test Product 1", "Added Test Product 1");

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total === 500, "Total Amount is correct");
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
		() => cur_frm.set_value("taxes_and_charges", "TEST In State GST"),
		() => frappe.timeout(0.3),
		() => cur_frm.save(),
		() => {
			// Check Address and Contact Info
			assert.ok(cur_frm.doc.address_display.includes("Billing Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.shipping_address.includes("Warehouse Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.contact_display == "Contact 1", "Contact info changed");

			// Check Currency
			assert.ok(cur_frm.doc_currency == "USD", "Currency Changed");
			assert.ok(cur_frm.doc.selling_price_list == "Test-Selling-USD", "Price List Changed");
			assert.ok(cur_frm.doc.items[0].rate == 200, "Price Changed Manually");
			assert.ok(cur_frm.doc.total == 1000, "New Total Calculated");

			// Check Terms and Condtions
			assert.ok(cur_frm.doc.tc_name == "Test Term 1", "Terms and Conditions Checked");

			// Check Taxes
			assert.ok(cur_frm.doc.taxes[0].account_head.includes("CGST"));
			assert.ok(cur_frm.doc.taxes[1].account_head.includes("SGST"));
			assert.ok(cur_frm.doc.grand_total == 1180, "Tax Amount Added to Total");
			assert.ok(cur_frm.doc.taxes_and_charges == "TEST In State GST", "Tax Template Selected");
		},
		() => frappe.timeout(0.3),
		() => cur_frm.print_doc(),
		() => frappe.timeout(1),
		() => assert.ok($('.btn-print-print').is(':visible'), "Print Format Available"),
		() => assert.ok(RegExp(/QTN-\d\d\d\d\d/g).test($("#header-html small").text())),
		() => assert.ok($(".important .text-right.value").text().includes("$ 1,180.00")),
		() => assert.ok($(".section-break+ .section-break .column-break:nth-child(1) .data-field:nth-child(1) .value").text().includes("Billing Street 1"), "Print Preview Works As Expected"),
		() => frappe.timeout(0.3),
		() => cur_frm.print_doc(),
		() => done()
	]);
});