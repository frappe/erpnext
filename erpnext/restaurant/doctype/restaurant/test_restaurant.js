/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Restaurant", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Restaurant
		() => frappe.tests.make('Restaurant', [
			// values to be set
			{name: 'Test Restaurant 1'},
			{company: '_Test Company 1'},
			{invoice_series_prefix: 'Test-Rest-1-Inv-'}
		]),
		() => {
			assert.equal(cur_frm.doc.company, '_Test Company 1');
		},
		() => done()
	]);

	frappe.run_serially([
		// insert a new Restaurant
		() => frappe.tests.make('Restaurant', [
			// values to be set
			{name: 'Test Restaurant 2'},
			{company: '_Test Company 1'},
			{invoice_series_prefix: 'Test-Rest-3-Inv-'}
		]),
		() => {
			assert.equal(cur_frm.doc.company, '_Test Company 2');
		},
		() => done()
	]);

});
