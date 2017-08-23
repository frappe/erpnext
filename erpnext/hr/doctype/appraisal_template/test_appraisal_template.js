QUnit.module('hr');

QUnit.test("Test: Appraisal Template [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		// Job Opening creation
		() => {
			frappe.tests.make('Appraisal Template', [
				{ kra_title: 'Test Appraisal 3'},
				{ description: 'This is just a test'},
				{ goals: [
					[
						{ kra: 'Design'},
						{ per_weightage: 50}
					],
					[
						{ kra: 'Code creation'},
						{ per_weightage: 50}
					]
				]},
			]);
		},
		() => frappe.timeout(3),
		() => {
			assert.equal('Test Appraisal 3',cur_frm.doc.kra_title, 'Appraisal name correctly set');
		},
		() => done()
	]);
});

