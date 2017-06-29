erpnext.selling_tests = {
	new_quotation: (assert) => {
		frappe.tests.require(['Customer', 'Item'])
		return new Promise((resolve) => {
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

QUnit.test("test sales cycle", function(assert) {
	let done = assert.async();
	frappe.test_data.customer_name = 'Test Customer ' + frappe.utils.get_random(10);

	erpnext.selling_tests.new_customer(assert)
		.then(() => {
			return erpnext.selling_tests.new_quotation(assert);
		})
		.then(() => { done(); });

});
