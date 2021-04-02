/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Fees", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially('Fees', [

		// insert a new Fees
		() => {
			return frappe.tests.make('Fees', [
				{student: 'STUD00001'},
				{due_date: frappe.datetime.get_today()},
				{fee_structure: 'FS00001'}
			]);
		},
		() => {
			assert.equal(cur_frm.doc.grand_total===cur_frm.doc.outstanding_amount);
		},
		() => frappe.timeout(0.3),
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => done()
	]);

});
