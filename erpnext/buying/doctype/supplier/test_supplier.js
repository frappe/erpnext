QUnit.module('Buying');

QUnit.test("test: supplier", function(assert) {
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Supplier', [
				{supplier_name: 'Test Supplier'},
				{supplier_type: 'Hardware'},
				{default_currency: 'INR'},
				{default_price_list: 'Standard Buying'},
				{accounts: [
					[
						{"company": 'Test Company'},
						{"account": 'Creditors - TC'}
					]]
				}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.supplier_name == 'Test Supplier', "Name correct");
			assert.ok(cur_frm.doc.supplier_type == 'Hardware', "Type correct");
			assert.ok(cur_frm.doc.default_currency == 'INR', "Currency correct");
			assert.ok(cur_frm.doc.accounts[0].account == 'Creditors - '+frappe.get_abbr('Test Company'), " Account Head abbr correct");
		},
		() => done()
	]);
});