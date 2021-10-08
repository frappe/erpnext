QUnit.module('Payment Entry');

QUnit.test("test payment entry", function(assert) {
	assert.expect(8);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Sales Invoice', [
				{customer: 'Test Customer 1'},
				{company: 'For Testing'},
				{currency: 'INR'},
				{selling_price_list: '_Test Price List'},
				{items: [
					[
						{'qty': 1},
						{'item_code': 'Test Product 1'},
					]
				]}
			]);
		},
		() => frappe.timeout(1),
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1.5),
		() => frappe.click_button('Close'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Make'),
		() => frappe.timeout(1),
		() => frappe.click_link('Payment'),
		() => frappe.timeout(2),
		() => cur_frm.set_value("paid_to", "_Test Cash - FT"),
		() => frappe.timeout(0.5),
		() => {
			assert.equal(frappe.get_route()[1], 'Payment Entry', 'made payment entry');
			assert.equal(cur_frm.doc.party, 'Test Customer 1', 'customer set in payment entry');
			assert.equal(cur_frm.doc.paid_from, 'Debtors - FT', 'customer account set in payment entry');
			assert.equal(cur_frm.doc.paid_amount, 100, 'paid amount set in payment entry');
			assert.equal(cur_frm.doc.references[0].allocated_amount, 100,
				'amount allocated against sales invoice');
		},
		() => cur_frm.set_value('paid_amount', 95),
		() => frappe.timeout(1),
		() => {
			frappe.model.set_value("Payment Entry Reference",
				cur_frm.doc.references[0].name, "allocated_amount", 100);
		},
		() => frappe.timeout(.5),
		() => {
			assert.equal(cur_frm.doc.difference_amount, 5, 'difference amount is 5');
		},
		() => {
			frappe.db.set_value("Company", "For Testing", "write_off_account", "_Test Write Off - FT");
			frappe.timeout(1);
			frappe.db.set_value("Company", "For Testing",
				"exchange_gain_loss_account", "_Test Exchange Gain/Loss - FT");
		},
		() => frappe.timeout(1),
		() => frappe.click_button('Write Off Difference Amount'),
		() => frappe.timeout(2),
		() => {
			assert.equal(cur_frm.doc.difference_amount, 0, 'difference amount is zero');
			assert.equal(cur_frm.doc.deductions[0].amount, 5, 'Write off amount = 5');
		},
		() => done()
	]);
});
