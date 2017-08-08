QUnit.module('Buying');

QUnit.test("test: request_for_quotation", function(assert) {
	assert.expect(11);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Request for Quotation', [
				{transaction_date: frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
				{company: 'Test Company'},
				{suppliers: [
					[
						{"supplier": 'Test Supplier'},
						{"email_id": 'test@supplier.com'}
					]
				]},
				{items: [
					[
						{"item_code": 'Test Product 1'},
						{"qty": 5},
						{"schedule_date": frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 3)},
						{"warehouse": 'All Warehouses - TC'}
					]
				]},
				{tc_name: 'Test Term 1'}	
			]);
		},
		() => {
			assert.ok(cur_frm.doc.transaction_date == frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1), "Date correct");
			assert.ok(cur_frm.doc.company == 'Test Company', "Company correct");
			assert.ok(cur_frm.doc.suppliers[0].supplier_name == 'Test Supplier', "Supplier name correct");
			assert.ok(cur_frm.doc.suppliers[0].contact == 'Contact 3-Test Supplier', "Contact correct");
			assert.ok(cur_frm.doc.suppliers[0].email_id == 'test@supplier.com', "Email id correct");
			assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 1', "Item Name correct");
			assert.ok(cur_frm.doc.items[0].warehouse == 'All Warehouses - TC', "Warehouse correct");
			assert.ok(cur_frm.doc.tc_name == 'Test Term 1', "Term name correct");
		},
		() => frappe.timeout(0.3),
	() => cur_frm.print_doc(),
	() => frappe.timeout(1),
	() => {
		assert.ok($('.btn-print-print').is(':visible'), "Print Format Available");
		assert.ok($(".section-break+ .section-break .column-break:nth-child(1) .value").text().includes("Test Product 1"), "Print Preview Works");
	},
	() => cur_frm.print_doc(),
	() => frappe.click_button('Submit'),
	() => frappe.click_button('Yes'),
	() => frappe.timeout(0.3),
	() => {
		assert.ok(cur_frm.doc.docstatus == 1, "Quotation request submitted");
	},
	() => done()
	]);
});