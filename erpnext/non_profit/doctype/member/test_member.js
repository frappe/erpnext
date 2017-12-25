/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Member", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Member
		() => frappe.tests.make('Member', [
			// values to be set
			{member_name: 'Test Member'},
			{membership_type: 'Gold'},
			{email: 'test@example.com'}
		]),
		() => {
			assert.equal(cur_frm.doc.membership_type, 'Gold');
			assert.equal(cur_frm.doc.email, 'test@example.com');
		},
		() => done()
	]);

});
