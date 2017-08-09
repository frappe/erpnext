QUnit.module('accounts');

QUnit.test('Create new Payment Term in quick view ', function(assert){
	assert.expect(4);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('List', 'Payment Term'),
		() => frappe.timeout(2),
		() => frappe.click_button('New'),
		// open in quick view
		() => frappe.timeout(2),
		() => {
			assert.ok(cur_dialog);
		},
		() => cur_dialog.set_value('code', '_COD'),
		() => cur_dialog.set_value('description', '_Cash on Delivery'),
		() => {
			assert.equal(cur_dialog.doc.code, '_COD');
			assert.equal(cur_dialog.doc.description, '_Cash on Delivery');
		},
		() => frappe.click_button('Save'),
		// confirm successful save
		() => frappe.click_button('Refresh'),
		() => frappe.timeout(2),
		() => {
			assert.ok(cur_list.data.some(obj => obj.name === '_COD'));
		},
		() => done()
	]);
});

QUnit.test('Create new Payment Term in full view ', function(assert){
	assert.expect(7);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('List', 'Payment Term'),
		() => frappe.timeout(2),
		() => frappe.click_button('New'),
		() => frappe.timeout(2),
		// open in full view
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value('code', '_2/10 N30'),
		() => cur_frm.set_value('description', '_2% Cash Discount within 10 days; Net 30 days'),
		() => cur_frm.set_value('term_days', '30'),
		() => frappe.click_link('Cash Discounts'),
		() => frappe.click_check('Include Cash Discount'),
		() => cur_frm.set_value('discount', 2),
		() => cur_frm.set_value('discount_days', 10),
		() => {
			assert.equal(cur_frm.doc.code, '_2/10 N30');
			assert.equal(cur_frm.doc.description, '_2% Cash Discount within 10 days; Net 30 days');
			assert.equal(cur_frm.doc.term_days, 30);
			assert.equal(cur_frm.doc.with_discount, 1);
			assert.equal(cur_frm.doc.discount, 2);
			assert.equal(cur_frm.doc.discount_days, 10);
		},
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		// confirm successful save
		() => frappe.set_route('List', 'Payment Term'),
		() => frappe.timeout(2),
		() => {
			assert.ok(cur_list.data.some(obj => obj.name === '_2/10 N30'));
		},
		() => done()
	]);
});

QUnit.test('Payment Term Validation', function(assert){
	assert.expect(8);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('List', 'Payment Term'),
		() => frappe.timeout(2.5),
		() => frappe.click_button('New'),
		() => frappe.timeout(2),
		// open in full view
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value('code', '_Test Code'),
		() => cur_frm.set_value('description', '_2% Cash Discount within 10 days; Net 30 days'),
		// validate numerical fields cannot be negative
		() => cur_frm.set_value('term_days', '-30'),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('term_days', 30),
		() => frappe.click_link('Cash Discounts'),
		() => frappe.click_check('Include Cash Discount'),
		() => cur_frm.set_value('discount', -22),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('discount', 2),
		() => cur_frm.set_value('discount_days', -10),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),

		// validate discount component
		() => cur_frm.set_value('term_days', 0),
		() => cur_frm.set_value('discount_days', 0),
		() => cur_frm.set_value('discount', 0),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('discount_days', 1),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('discount_days', 0),
		() => cur_frm.set_value('discount', 2),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('discount', 2),
		() => cur_frm.set_value('discount_days', 10),
		() => cur_frm.set_value('term_days', 0),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => {
			// dialog is shown
			assert.ok(cur_dialog);
		},
		() => frappe.click_button('Close'),
		() => cur_frm.set_value('term_days', 30),
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),

		// confirm successful save
		() => frappe.set_route('List', 'Payment Term'),
		() => frappe.timeout(2),
		() => {
			assert.ok(cur_list.data.some(obj => obj.name === '_Test Code'));
		},
		() => done()
	]);
});