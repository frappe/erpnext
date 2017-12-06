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
			{applicant_name: 'Test Organization'},
			{contact_person:'Test Applicant'},
			{email: 'test@example.com'},
			{grant_description:'Test message'},
			{amount: 150000}
		]),
		() => {
			assert.equal(cur_frm.doc.applicant_name, 'Test Organization');
			assert.equal(cur_frm.doc.contact_person, 'Test Applicant');
			assert.equal(cur_frm.doc.email, 'test@example.com');
			assert.equal(cur_frm.doc.amount, 150000);
		},
		() => done()
	]);

});
