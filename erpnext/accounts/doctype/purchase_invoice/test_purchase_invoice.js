QUnit.module('Purchase Invoice');

QUnit.test("test purchase invoice", function(assert) {
	assert.expect(9);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Invoice', [
				{supplier: 'Test Supplier'},
				{bill_no: 'in123'},
				{items: [
					[
						{'qty': 5},
						{'item_code': 'Test Product 1'},
						{'rate':100},
					]
				]},
				{update_stock:1},
				{supplier_address: 'Test1-Billing'},
				{contact_person: 'Contact 3-Test Supplier'},
				{taxes_and_charges: 'TEST In State GST - FT'},
				{tc_name: 'Test Term 1'},
				{terms: 'This is Test'},
				{payment_terms_template: '_Test Payment Term Template UI'}
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1', "Item name correct");
			// get tax details
			assert.ok(cur_frm.doc.taxes_and_charges=='TEST In State GST - FT', "Tax details correct");
			// get tax account head details
			assert.ok(cur_frm.doc.taxes[0].account_head=='CGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')), " Account Head abbr correct");
			// grand_total Calculated
			assert.ok(cur_frm.doc.grand_total==590, "Grad Total correct");

			assert.ok(cur_frm.doc.payment_terms_template, "Payment Terms Template is correct");
			assert.ok(cur_frm.doc.payment_schedule.length > 0, "Payment Term Schedule is not empty");

		},
		() => {
			let date = cur_frm.doc.due_date;
			frappe.tests.set_control('due_date', frappe.datetime.add_days(date, 1));
			frappe.timeout(0.5);
			assert.ok(cur_dialog && cur_dialog.is_visible, 'Message is displayed to user');
		},
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(0.5),
		() => frappe.tests.set_form_values(cur_frm, [{'payment_terms_schedule': ''}]),
		() => {
			let date = cur_frm.doc.due_date;
			frappe.tests.set_control('due_date', frappe.datetime.add_days(date, 1));
			frappe.timeout(0.5);
			assert.ok(cur_dialog && cur_dialog.is_visible, 'Message is displayed to user');
		},
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(0.5),
		() => frappe.tests.set_form_values(cur_frm, [{'payment_schedule': []}]),
		() => {
			let date = cur_frm.doc.due_date;
			frappe.tests.set_control('due_date', frappe.datetime.add_days(date, 1));
			frappe.timeout(0.5);
			assert.ok(!cur_dialog, 'Message is not shown');
		},
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => done()
	]);
});
