erpnext.selling_tests = {
	new_quotation: (assert) => {
		frappe.tests.require(['Customer', 'Item'])
		return new Promise(resolve => {
			frappe.set_route('List', 'Quotation')
				.then(() => {
					return frappe.new_doc('Quotation')
				})
				.then(() => {
					return cur_frm
						.get_field('customer')
						.set_value(frappe.tests.get_any('Customer'));
				})
				.then(() => {
					return cur_frm
						.get_field('items').grid
						.get_row(0)
						.activate()
						.get_field('item_code')
						.set_value(frappe.tests.get_any('Item'));
				})
				.then(() => {
					return cur_frm.save()
				})
				.then(() => {
					assert.ok(!cur_frm.doc.is_new());
					assert.ok(!cur_frm.doc.is_new());
					resolve();
				});
		});
	}
};

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
		},
		() => done()
	]);
});
