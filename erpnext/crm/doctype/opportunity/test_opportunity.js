QUnit.test("test: opportunity", function (assert) {
	assert.expect(8);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('List', 'Opportunity'),
		() => frappe.timeout(1),
		() => frappe.click_button('New'),
		() => frappe.timeout(1),
		() => cur_frm.set_value('enquiry_from', 'Customer'),
		() => cur_frm.set_value('customer', 'Test Customer 1'),

		// check items
		() => cur_frm.set_value('with_items', 1),
		() => frappe.tests.set_grid_values(cur_frm, 'items', [
			[
				{item_code:'Test Product 1'},
				{qty: 4}
			]
		]),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => {
			assert.notOk(cur_frm.is_new(), 'saved');
			frappe.opportunity_name = cur_frm.doc.name;
		},

		// close and re-open
		() => frappe.click_button('Close'),
		() => frappe.timeout(1),
		() => assert.equal(cur_frm.doc.status, 'Closed',
			'closed'),

		() => frappe.click_button('Reopen'),
		() => assert.equal(cur_frm.doc.status, 'Open',
			'reopened'),
		() => frappe.timeout(1),

		// make quotation
		() => frappe.click_button('Make'),
		() => frappe.click_link('Quotation', 1),
		() => frappe.timeout(2),
		() => {
			assert.equal(frappe.get_route()[1], 'Quotation',
				'made quotation');
			assert.equal(cur_frm.doc.customer, 'Test Customer 1',
				'customer set in quotation');
			assert.equal(cur_frm.doc.items[0].item_code, 'Test Product 1',
				'item set in quotation');
			assert.equal(cur_frm.doc.items[0].qty, 4,
				'qty set in quotation');
			assert.equal(cur_frm.doc.items[0].prevdoc_docname, frappe.opportunity_name,
				'opportunity set in quotation');
		},
		() => done()
	]);
});
