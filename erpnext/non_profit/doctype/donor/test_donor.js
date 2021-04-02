/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Donor", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(3);

	frappe.run_serially([
		// insert a new Member
		() => frappe.tests.make('Donor', [
			// values to be set
			{donor_name: 'Test Donor'},
			{donor_type: 'Test Organization'},
			{email: 'test@example.com'}
		]),
		() => {
			assert.equal(cur_frm.doc.donor_name, 'Test Donor');
			assert.equal(cur_frm.doc.donor_type, 'Test Organization');
			assert.equal(cur_frm.doc.email, 'test@example.com');
		},
		() => done()
	]);

});
