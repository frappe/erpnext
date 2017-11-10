// Education Assessment module
QUnit.module('education');

QUnit.test('Test: Assessment Result Tool', function(assert){
	assert.expect(1);
	let done = assert.async();
	let i, count = 0, assessment_name;

	frappe.run_serially([
		// Saving Assessment Plan name
		() => frappe.db.get_value('Assessment Plan', {'assessment_name': 'Test-Mid-Term'}, 'name'),
		(assessment_plan) => {assessment_name = assessment_plan.message.name;},

		() => frappe.set_route('Form', 'Assessment Plan', assessment_name),
		() => frappe.timeout(1),
		() => frappe.tests.click_button('Assessment Result'),
		() => frappe.timeout(1),
		() => cur_frm.refresh(),
		() => frappe.timeout(1),
		() => {
			for(i = 2; i < $('tbody tr').size() * 4; i = (i + 4)){
				if(($(`tbody td:eq("${i}")`) != "") && ($(`tbody td:eq("${i+1}")`) != ""))
					count++;
			}
			assert.equal($('tbody tr').size(), count, 'All grades correctly displayed');
		},
		() => done()
	]);
});