/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Restaurant", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);
	let customer =  {
		"Test Customer 1": [
			{customer_name: "Test Customer 1"}
		],
		"Test Customer 2": [
			{customer_name: "Test Customer 2"}
		]
	};

	frappe.run_serially([
		// insert a new Restaurant
		() => frappe.tests.setup_doctype('Customer', customer),				
		() => {
			return frappe.tests.make('Restaurant', [
				// values to be set
				{__newname: 'Test Restaurant 1'},
				{company: 'Test Company'},
				{invoice_series_prefix: 'Test-Rest-1-Inv-'},
				{default_customer: 'Test Customer 1'}
			])
		},
		() => frappe.timeout(3),
		() => {
			assert.equal(cur_frm.doc.company, 'Test Company');
		},
		() => {
			return frappe.tests.make('Restaurant', [
				// values to be set
				{__newname: 'Test Restaurant 2'},
				{company: 'Test Company'},
				{invoice_series_prefix: 'Test-Rest-3-Inv-'},
				{default_customer: 'Test Customer 2'}
			]);
		},
		() => frappe.timeout(3),
		() => {
			assert.equal(cur_frm.doc.company, 'Test Company');
		},
		() => done()
	]);
});
