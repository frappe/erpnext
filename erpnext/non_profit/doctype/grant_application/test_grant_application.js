/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Grant Application", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(4);

	frappe.run_serially([
		// insert a new Member
		() => frappe.tests.make('Grant Application', [
			// values to be set
			{organization: 'Test Organization'},
			{grant_applicant_name:'Test Applicant'},
			{email: 'test@example.com'},
			{grant_description:'Test message'},
			{grant_purpose: 'Test Meesage'},
			{amount: 150000},
			{grant_past_record:'NO'}
		]),
		() => {
			assert.equal(cur_frm.doc.organization, 'Test Organization');
			assert.equal(cur_frm.doc.grant_applicant_name, 'Test Applicant');
			assert.equal(cur_frm.doc.email, 'test@example.com');
			assert.equal(cur_frm.doc.amount, 150000);
		},
		() => done()
	]);

});
