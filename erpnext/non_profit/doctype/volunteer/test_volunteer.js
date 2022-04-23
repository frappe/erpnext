/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Volunteer", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(4);

	frappe.run_serially([
		// insert a new Member
		() => frappe.tests.make('Volunteer', [
			// values to be set
			{volunteer_name: 'Test Volunteer'},
			{volunteer_type:'Test Work'},
			{email:'test@example.com'},
			{'availability': 'Weekends'},
			{volunteer_skills:[
					[
						{'volunteer_skills': 'Fundraiser'},
					]
			]},
		]),
		() => {
			assert.equal(cur_frm.doc.volunteer_name, 'Test Volunteer');
			assert.equal(cur_frm.doc.volunteer_type, 'Test Work');
			assert.equal(cur_frm.doc.email, 'test@example.com');
			assert.equal(cur_frm.doc.availability, 'Weekends');
		},
		() => done()
	]);

});
