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
						{'item_code': 'Test Product 1'},
						{'qty': 1},
						{'rate': 101},
					]
				]}
			]);
		},
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(1),
		() => frappe.click_button('Make'),
		() => frappe.timeout(1),
		() => frappe.click_link('Payment'),
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
		() => frappe.timeout(1),
		() => cur_frm.set_value('paid_amount', 100),
		() => frappe.timeout(1),
		() => {
			frappe.model.set_value("Payment Entry Reference", cur_frm.doc.references[0].name,
				"allocated_amount", 101);
		},
		() => frappe.timeout(1),
		() => frappe.click_button('Write Off Difference Amount'),
		() => frappe.timeout(1),
		() => {
			assert.equal(cur_frm.doc.difference_amount, 0, 'difference amount is zero');
			assert.equal(cur_frm.doc.deductions[0].amount, 1, 'Write off amount = 1');
		},
		() => done()
	]);
});
