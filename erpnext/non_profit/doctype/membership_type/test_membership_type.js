/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Membership Type", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Member
		() => frappe.tests.make('Membership Type', [
			// values to be set
			{membership_type: 'Gold'},
			{amount:50000}
		]),
		() => {
			assert.equal(cur_frm.doc.membership_type, 'Gold');
			assert.equal(cur_frm.doc.amount, '50000');
		},
		() => done()
	]);

});
