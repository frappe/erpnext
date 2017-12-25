/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Land Unit", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		// insert a new Land Unit
		() => frappe.tests.make('Land Unit', [
			// values to be set
			{land_unit_name: 'Basil Farm'}
		]),
		() => {
			assert.equal(cur_frm.doc.name, 'Basil Farm');
		},
		() => done()
	]);

});
