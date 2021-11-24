context('Organizational Chart', () => {
	before(() => {
		cy.login();
		cy.visit('/app/website');
	});

	it('navigates to org chart', () => {
		cy.visit('/app');
		cy.visit('/app/organizational-chart');
		cy.url().should('include', '/organizational-chart');

		cy.window().its('frappe.csrf_token').then(csrf_token => {
			return cy.request({
				url: `/api/method/erpnext.tests.ui_test_helpers.create_employee_records`,
				method: 'POST',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': csrf_token
				},
				timeout: 60000
			}).then(res => {
				expect(res.status).eq(200);
				cy.get('.frappe-control[data-fieldname=company] input').focus().as('input');
				cy.get('@input')
					.clear({ force: true })
					.type('Test Org Chart{downarrow}{enter}', { force: true })
					.blur({ force: true });
			});
		});
	});

	it('renders root nodes and loads children for the first expandable node', () => {
		// check rendered root nodes and the node name, title, connections
		cy.get('.hierarchy').find('.root-level ul.node-children').children()
			.should('have.length', 2)
			.first()
			.as('first-child');

		cy.get('@first-child').get('.node-name').contains('Test Employee 1');
		cy.get('@first-child').get('.node-info').find('.node-title').contains('CEO');
		cy.get('@first-child').get('.node-info').find('.node-connections').contains('· 2 Connections');

		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			// children of 1st root visible
			cy.get(`div[data-parent="${employee_records.message[0]}"]`).as('child-node');
			cy.get('@child-node')
				.should('have.length', 1)
				.should('be.visible');
			cy.get('@child-node').get('.node-name').contains('Test Employee 3');

			// connectors between first root node and immediate child
			cy.get(`path[data-parent="${employee_records.message[0]}"]`)
				.should('be.visible')
				.invoke('attr', 'data-child')
				.should('equal', employee_records.message[2]);
		});
	});

	it('hides active nodes children and connectors on expanding sibling node', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			// click sibling
			cy.get(`#${employee_records.message[1]}`)
				.click()
				.should('have.class', 'active');

			// child nodes and connectors hidden
			cy.get(`[data-parent="${employee_records.message[0]}"]`).should('not.be.visible');
			cy.get(`path[data-parent="${employee_records.message[0]}"]`).should('not.be.visible');
		});
	});

	it('collapses previous level nodes and refreshes connectors on expanding child node', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			// click child node
			cy.get(`#${employee_records.message[3]}`)
				.click()
				.should('have.class', 'active');

			// previous level nodes: parent should be on active-path; other nodes should be collapsed
			cy.get(`#${employee_records.message[0]}`).should('have.class', 'collapsed');
			cy.get(`#${employee_records.message[1]}`).should('have.class', 'active-path');

			// previous level connectors refreshed
			cy.get(`path[data-parent="${employee_records.message[1]}"]`)
				.should('have.class', 'collapsed-connector');

			// child node's children and connectors rendered
			cy.get(`[data-parent="${employee_records.message[3]}"]`).should('be.visible');
			cy.get(`path[data-parent="${employee_records.message[3]}"]`).should('be.visible');
		});
	});

	it('expands previous level nodes', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			cy.get(`#${employee_records.message[0]}`)
				.click()
				.should('have.class', 'active');

			cy.get(`[data-parent="${employee_records.message[0]}"]`)
				.should('be.visible');

			cy.get('ul.hierarchy').children().should('have.length', 2);
			cy.get(`#connectors`).children().should('have.length', 1);
		});
	});

	it('edit node navigates to employee master', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			cy.get(`#${employee_records.message[0]}`).find('.btn-edit-node')
				.click();

			cy.url().should('include', `/employee/${employee_records.message[0]}`);
		});
	});
});
