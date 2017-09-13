QUnit.module('Payment Entry');

QUnit.test("test payment entry", function(assert) {
	assert.expect(6);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Sales Invoice', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'qty': 1},
						{'rate': 101},
						{'item_code': 'Test Product 1'},
					]
				]}
			]);
		},
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Make'),
		() => frappe.click_link('Payment', 1),
		() => frappe.timeout(2),
		() => {
			assert.equal(frappe.get_route()[1], 'Payment Entry',
				'made payment entry');
			assert.equal(cur_frm.doc.party, 'Test Customer 1',
				'customer set in payment entry');
			assert.equal(cur_frm.doc.paid_amount, 101,
				'paid amount set in payment entry');
			assert.equal(cur_frm.doc.references[0].allocated_amount, 101,
				'amount allocated against sales invoice');
		},
		() => cur_frm.set_value('paid_amount', 100),
		() => {
			cur_frm.doc.references[0].allocated_amount = 101;
		},
		() => frappe.click_button('Write Off Difference Amount'),
		() => {
			assert.equal(cur_frm.doc.difference_amount, 0,
				'difference amount is zero');
			assert.equal(cur_frm.doc.deductions[0].amount, 1,
				'Write off amount = 1');
		},
		() => done()
	]);
});
