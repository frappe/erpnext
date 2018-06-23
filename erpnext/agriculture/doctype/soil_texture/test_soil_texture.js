/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Soil Texture", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Soil Texture
		() => frappe.tests.make('Soil Texture', [
			// values to be set
			{location: '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[72.882185,19.076395]}}]}'},
			{collection_datetime: '2017-11-08'},
			{clay_composition: 20},
			{sand_composition: 30}
		]),
		() => {
			assert.equal(cur_frm.doc.silt_composition, 50);
			assert.equal(cur_frm.doc.soil_type, 'Silt Loam');
		},
		() => done()
	]);
});
