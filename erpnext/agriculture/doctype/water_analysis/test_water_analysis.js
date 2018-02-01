/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Water Analysis", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		// insert a new Water Analysis
		() => frappe.tests.make('Water Analysis', [
			// values to be set
			{location: '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[72.882185,19.076395]}}]}'},
			{collection_datetime: '2017-11-08 18:43:57'},
			{laboratory_testing_datetime: '2017-11-10 18:43:57'}
		]),
		() => {
			assert.equal(cur_frm.doc.result_datetime, '2017-11-10 18:43:57');
		},
		() => done()
	]);

});
