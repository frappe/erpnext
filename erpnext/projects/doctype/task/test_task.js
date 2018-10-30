
QUnit.test("test: Task", function (assert) {
	let done = assert.async();
	assert.expect(2);

	frappe.run_serially([
		() => frappe.tests.make('Task Description',[
			{title:"Test Desc One"},
			{task_description:"Without Jinja"}
		]),
		() => frappe.tests.make('Task Description',[
			{title:"Test Desc Two"},
			{task_description:"With Jinja subject = {{subject}}"}
		]),
		() => frappe.timeout(2),
		() => frappe.tests.make('Task', [
			{subject: '_Test Task1'},
			{task_description: 'Test Desc One'}
		]),
		() => {
			assert.equal(cur_frm.doc.description, 'Without Jinja');
		},
		() => frappe.tests.make('Task', [
			{subject: '_Test Task2'},
			{task_description: 'Test Desc Two'}
		]),
		() => {
			assert.equal(cur_frm.doc.description, 'With Jinja subject = _Test Task2');
		},
		() => done()
	]);

});
