/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Task", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Task
		() => frappe.tests.make('Task', [
			// values to be set
			{subject: 'new task'}
		]),
		() => {
			assert.equal(cur_frm.doc.status, 'Open');
			assert.equal(cur_frm.doc.priority, 'Low');
		},
		() => done()
	]);

});
