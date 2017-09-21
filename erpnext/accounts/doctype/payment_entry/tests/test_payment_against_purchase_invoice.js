QUnit.module('Payment Entry');

QUnit.test("test payment entry", function(assert) {
	assert.expect(5);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Payment Entry', [
				{payment_type:'Pay'},
				{company:'For Testing'},
				{party_type:'Supplier'},
				{party:'Test Supplier'},
				{paid_from:'Cash - FT'}
			]);
		},
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(2),
		() => frappe.timeout(3),
		() => {
			assert.equal(cur_frm.doc.party, 'Test Supplier',
				'supplier set in payment entry');
			assert.equal(cur_frm.doc.paid_amount, 590,
				'paid amount set in payment entry');
			assert.equal(cur_frm.doc.references[0].outstanding_amount, 590,
				'amount allocated against purchase invoice');
			assert.equal(cur_frm.doc.references[0].bill_no, 'in123',
				'invoice number correctly mapped against purchase invoice');
		},
		() => frappe.timeout(3),
		() => frappe.set_route('List','Payment Entry','List'),
		() => frappe.timeout(3),

		// Checking the submission of payment entry
		() => {
			assert.ok(cur_list.data[0].docstatus==1,'Submitted successfully');
		},
		() => done()
	]);
});
