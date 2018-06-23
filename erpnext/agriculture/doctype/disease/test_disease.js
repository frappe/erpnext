/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Disease", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		// insert a new Disease
		() => frappe.tests.make('Disease', [
			// values to be set
			{common_name: 'Aphids'},
			{scientific_name: 'Aphidoidea'},
			{treatment_task: [
				[
					{task_name: "Survey and find the aphid locations"},
					{start_day: 1},
					{end_day: 2},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "Apply Pesticides"},
					{start_day: 3},
					{end_day: 3},
					{holiday_management: "Ignore holidays"}
				]
			]}
		]),
		() => {
			assert.equal(cur_frm.doc.treatment_period, 3);
		},
		() => done()
	]);

});

