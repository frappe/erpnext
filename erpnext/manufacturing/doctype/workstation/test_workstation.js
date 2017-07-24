QUnit.test("test: workstation", function (assert) {
	assert.expect(9);
	let done = assert.async();
	let elec_rate = 50;
	let rent = 100;
	let consumable_rate = 20;
	let labour_rate = 500;
	frappe.run_serially([
		// test workstation creation
		() => frappe.set_route("List", "Workstation"),

		// Create a keyboard workstation
		() => frappe.tests.make(
			"Workstation", [
				{workstation_name: "Keyboard assembly workstation"},
				{hour_rate_electricity: elec_rate},
				{hour_rate_rent: rent},
				{hour_rate_consumable: consumable_rate},
				{hour_rate_labour: labour_rate},
				{working_hours: [
					[
						{enabled: 1},
						{start_time: '11:00:00'},
						{end_time: '18:00:00'}
					]
				]}
			]
		),
		() => {
			assert.ok(cur_frm.doc.workstation_name.includes('Keyboard assembly workstation'),
				'Keyboard assembly workstation created successfully');
			assert.equal(cur_frm.doc.hour_rate_electricity, elec_rate,
				'electricity rate set correctly');
			assert.equal(cur_frm.doc.hour_rate_rent, rent,
				'rent set correctly');
			assert.equal(cur_frm.doc.hour_rate_consumable, consumable_rate,
				'consumable rate set correctly');
			assert.equal(cur_frm.doc.hour_rate_labour, labour_rate,
				'labour rate set correctly');
			assert.equal(cur_frm.doc.working_hours[0].enabled, 1,
				'working hours enabled');
			assert.ok(cur_frm.doc.working_hours[0].start_time.includes('11:00:0'),
				'start time set correctly');
			assert.ok(cur_frm.doc.working_hours[0].end_time.includes('18:00:0'),
				'end time set correctly');
			assert.ok(cur_frm.doc.hour_rate_electricity+cur_frm.doc.hour_rate_rent+
				cur_frm.doc.hour_rate_consumable+cur_frm.doc.hour_rate_labour==
				cur_frm.doc.hour_rate, 'Net hour rate set correctly');
		},

		// Create a Screen workstation
		() => frappe.tests.make(
			"Workstation", [
				{workstation_name: "Screen assembly workstation"},
				{hour_rate_electricity: elec_rate},
				{hour_rate_rent: rent},
				{hour_rate_consumable: consumable_rate},
				{hour_rate_labour: labour_rate},
				{working_hours: [
					[
						{enabled: 1},
						{start_time: '11:00:00'},
						{end_time: '18:00:00'}
					]
				]}
			]
		),

		// Create a CPU workstation
		() => frappe.tests.make(
			"Workstation", [
				{workstation_name: "CPU assembly workstation"},
				{hour_rate_electricity: elec_rate},
				{hour_rate_rent: rent},
				{hour_rate_consumable: consumable_rate},
				{hour_rate_labour: labour_rate},
				{working_hours: [
					[
						{enabled: 1},
						{start_time: '11:00:00'},
						{end_time: '18:00:00'}
					]
				]}
			]
		),

		() => done()
	]);
});
