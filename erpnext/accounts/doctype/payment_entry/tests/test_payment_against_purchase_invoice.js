QUnit.module('Payment Entry');

QUnit.test("test payment entry", function(assert) {
	assert.expect(7	);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Invoice', [
				{supplier: 'Test Supplier'},
				{bill_no: 'in1234'},
				{items: [
					[
						{'qty': 2},
						{'item_code': 'Test Product 1'},
						{'rate':1000},
					]
				]},
				{update_stock:1},
				{supplier_address: 'Test1-Billing'},
				{contact_person: 'Contact 3-Test Supplier'},
				{tc_name: 'Test Term 1'},
				{terms: 'This is just a Test'}
			]);
		},

		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => frappe.click_button('Make'),
		() => frappe.timeout(2),
		() => frappe.click_link('Payment'),
		() => frappe.timeout(3),
		() => cur_frm.set_value('mode_of_payment','Cash'),
		() => frappe.timeout(3),
		() => {
			assert.equal(frappe.get_route()[1], 'Payment Entry',
				'made payment entry');
			assert.equal(cur_frm.doc.party, 'Test Supplier',
				'supplier set in payment entry');
			assert.equal(cur_frm.doc.paid_amount, 2000,
				'paid amount set in payment entry');
			assert.equal(cur_frm.doc.references[0].allocated_amount, 2000,
				'amount allocated against purchase invoice');
			assert.equal(cur_frm.doc.references[0].bill_no, 'in1234',
				'invoice number allocated against purchase invoice');
			assert.equal(cur_frm.get_field('total_allocated_amount').value, 2000,
				'correct amount allocated in Write Off');
			assert.equal(cur_frm.get_field('unallocated_amount').value, 0,
				'correct amount unallocated in Write Off');
		},

		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(3),
		() => done()
	]);
});