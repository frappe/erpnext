QUnit.module('accounts');

QUnit.test('Create new Payment Due Date in quick view ', function(assert){
	assert.expect(3);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('List', 'Payment Due Date'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('New'),
		// open in quick view
		() => cur_dialog.set_value('code', '_COD'),
		() => cur_dialog.set_value('description', '_Cash on Delivery'),
		() => {
			assert.equal(cur_dialog.doc.code, '_COD');
			assert.equal(cur_dialog.doc.description, '_Cash on Delivery')
		},
		() => frappe.click_button('Save'),
		// confirm successful save
		() => frappe.click_button('Refresh'),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_list.data.some(obj => obj.name === '_COD'))
		},
		() => done()
	]);
});

QUnit.test('Create new Payment Due Date in full view ', function(assert){
	assert.expect(7);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('List', 'Payment Due Date'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('New'),
		// open in full view
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value('code', '_2/10 N30'),
		() => cur_frm.set_value('description', '_2% Cash Discount within 10 days; Net 30 days'),
		() => cur_frm.set_value('term_days', '30'),
		() => frappe.click_link('Cash Discounts'),
		() => frappe.click_check('Include Cash Discount'),
		() => cur_frm.set_value('discount_percentage', 2),
		() => cur_frm.set_value('discount_days', 10),
		() => {
			assert.equal(cur_frm.doc.code, '_2/10 N30');
			assert.equal(cur_frm.doc.description, '_2% Cash Discount within 10 days; Net 30 days');
			assert.equal(cur_frm.doc.term_days, 30);
			assert.equal(cur_frm.doc.with_discount, 1),
			assert.equal(cur_frm.doc.discount_percentage, 2),
			assert.equal(cur_frm.doc.discount_days, 10)
		},
		() => frappe.click_button('Save'),
		() => frappe.timeout(1),
		// confirm successful save
		() => frappe.set_route('List', 'Payment Due Date'),
		() => frappe.timeout(0.5),
		() => {
			assert.ok(cur_list.data.some(obj => obj.name === '_2/10 N30'))
		},
		() => done()
	]);
});