QUnit.module('Buying');

QUnit.test("test: supplier quotation", function(assert) {
	assert.expect(11);
	let done = assert.async();
	let date;

	frappe.run_serially([
		() => {
			date = frappe.datetime.add_days(frappe.datetime.now_date(), 10);
			return frappe.tests.make('Supplier Quotation', [
				{supplier: 'Test Supplier'},
				{transaction_date: date},
				{currency: 'INR'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"uom": 'Unit'},
						{"rate": 200},
						{"warehouse": 'All Warehouses - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]},
				{apply_discount_on: 'Grand Total'},
				{additional_discount_percentage: 10},
				{tc_name: 'Test Term 1'},
				{terms: 'This is a term'}
			]);
		},
		() => {
			// Get Supplier details
			assert.ok(cur_frm.doc.supplier == 'Test Supplier', "Supplier correct");
			assert.ok(cur_frm.doc.company == cur_frm.doc.company, "Company correct");
			// Get Contact details
			assert.ok(cur_frm.doc.contact_display == 'Contact 3', "Conatct correct");
			assert.ok(cur_frm.doc.contact_email == 'test@supplier.com', "Email correct");
			// Get uom
			assert.ok(cur_frm.doc.items[0].uom == 'Unit', "Multi uom correct");
			assert.ok(cur_frm.doc.total ==  1000, "Total correct");
			// Calculate total after discount
			assert.ok(cur_frm.doc.grand_total ==  900, "Grand total correct");
			// Get terms
			assert.ok(cur_frm.doc.tc_name == 'Test Term 1', "Terms correct");
		},

		() => cur_frm.print_doc(),
		() => frappe.timeout(2),
		() => {
			assert.ok($('.btn-print-print').is(':visible'), "Print Format Available");
			assert.ok($("table > tbody > tr > td:nth-child(3) > div").text().includes("Test Product 4"), "Print Preview Works As Expected");
		},
		() => cur_frm.print_doc(),
		() => frappe.timeout(1),
		() => frappe.click_button('Get items from'),
		() => frappe.timeout(0.3),
		() => frappe.click_link('Material Request'),
		() => frappe.timeout(0.3),
		() => frappe.click_button('Get Items'),
		() => frappe.timeout(1),
		() => {
			// Get item from Material Requests
			assert.ok(cur_frm.doc.items[1].item_name == 'Test Product 1', "Getting items from material requests work");
		},

		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),

		() => done()
	]);
});