QUnit.module('sales');

QUnit.test("test quotation", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.tests.setup_doctype('Customer'),
		() => frappe.tests.setup_doctype('Item'),
		() => {
			return frappe.tests.make('Quotation', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 5}
					]
				]}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1');

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total==500);
			console.log(cur_frm.doc.items[0].get_item_details);
		},
		() => done()
	]);
});

//QUnit.module('sales');

QUnit.only("test lead", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Lead', [
				{lead_name: 'Test Customer 1'},
				{status: 'Lead'}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.lead_name=='Test Customer 1');

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.status=='Lead');
		},
		() => done()
	]);
});