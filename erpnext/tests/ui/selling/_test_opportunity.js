QUnit.test("test: opportunity", function (assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Opportunity", [{
				enquiry_from: "Lead"
			},
			{
				lead: "LEAD-00002"
			}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.lead === "LEAD-00002");
			return done();
		}
	]);
});
