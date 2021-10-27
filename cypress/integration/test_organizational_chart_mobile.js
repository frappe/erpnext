context('Organizational Chart Mobile', () => {
	before(() => {
		cy.login();
		cy.visit('/app/website');
	});

	it('navigates to org chart', () => {
		cy.viewport(375, 667);
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

	it('renders root nodes', () => {
		// check rendered root nodes and the node name, title, connections
		cy.get('.hierarchy-mobile').find('.root-level').children()
			.should('have.length', 2)
			.first()
			.as('first-child');

		cy.get('@first-child').get('.node-name').contains('Test Employee 1');
		cy.get('@first-child').get('.node-info').find('.node-title').contains('CEO');
		cy.get('@first-child').get('.node-info').find('.node-connections').contains('· 2');
	});

	it('expands root node', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			cy.get(`#${employee_records.message[1]}`)
				.click()
				.should('have.class', 'active');

			// other root node removed
			cy.get(`#${employee_records.message[0]}`).should('not.exist');

			// children of active root node
			cy.get('.hierarchy-mobile').find('.level').first().find('ul.node-children').children()
				.should('have.length', 2);

			cy.get(`div[data-parent="${employee_records.message[1]}"]`).first().as('child-node');
			cy.get('@child-node').should('be.visible');

			cy.get('@child-node')
				.get('.node-name')
				.contains('Test Employee 4');

			// connectors between root node and immediate children
			cy.get(`path[data-parent="${employee_records.message[1]}"]`).as('connectors');
			cy.get('@connectors')
				.should('have.length', 2)
				.should('be.visible');

			cy.get('@connectors')
				.first()
				.invoke('attr', 'data-child')
				.should('eq', employee_records.message[3]);
		});
	});

	it('expands child node', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			cy.get(`#${employee_records.message[3]}`)
				.click()
				.should('have.class', 'active')
				.as('expanded_node');

			// 2 levels on screen; 1 on active path; 1 collapsed
			cy.get('.hierarchy-mobile').children().should('have.length', 2);
			cy.get(`#${employee_records.message[1]}`).should('have.class', 'active-path');

			// children of expanded node visible
			cy.get('@expanded_node')
				.next()
				.should('have.class', 'node-children')
				.as('node-children');

			cy.get('@node-children').children().should('have.length', 1);
			cy.get('@node-children')
				.first()
				.get('.node-card')
				.should('have.class', 'active-child')
				.contains('Test Employee 7');

			// orphan connectors removed
			cy.get(`#connectors`).children().should('have.length', 2);
		});
	});

	it('renders sibling group', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			// sibling group visible for parent
			cy.get(`#${employee_records.message[1]}`)
				.next()
				.as('sibling_group');

			cy.get('@sibling_group')
				.should('have.attr', 'data-parent', 'undefined')
				.should('have.class', 'node-group')
				.and('have.class', 'collapsed');

			cy.get('@sibling_group').get('.avatar-group').children().as('siblings');
			cy.get('@siblings').should('have.length', 1);
			cy.get('@siblings')
				.first()
				.should('have.attr', 'title', 'Test Employee 1');

		});
	});

	it('expands previous level nodes', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			cy.get(`#${employee_records.message[6]}`)
				.click()
				.should('have.class', 'active');

			// clicking on previous level node should remove all the nodes ahead
			// and expand that node
			cy.get(`#${employee_records.message[3]}`).click();
			cy.get(`#${employee_records.message[3]}`)
				.should('have.class', 'active')
				.should('not.have.class', 'active-path');

			cy.get(`#${employee_records.message[6]}`).should('have.class', 'active-child');
			cy.get('.hierarchy-mobile').children().should('have.length', 2);
			cy.get(`#connectors`).children().should('have.length', 2);
		});
	});

	it('expands sibling group', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(employee_records => {
			// sibling group visible for parent
			cy.get(`#${employee_records.message[6]}`).click();

			cy.get(`#${employee_records.message[3]}`)
				.next()
				.click();

			// siblings of parent should be visible
			cy.get('.hierarchy-mobile').prev().as('sibling_group');
			cy.get('@sibling_group')
				.should('exist')
				.should('have.class', 'sibling-group')
				.should('not.have.class', 'collapsed');

			cy.get(`#${employee_records.message[1]}`)
				.should('be.visible')
				.should('have.class', 'active');

			cy.get(`[data-parent="${employee_records.message[1]}"]`)
				.should('be.visible')
				.should('have.length', 2)
				.should('have.class', 'active-child');
		});
	});

	it('goes to the respective level after clicking on non-collapsed sibling group', () => {
		cy.call('erpnext.tests.ui_test_helpers.get_employee_records').then(() => {
			// click on non-collapsed sibling group
			cy.get('.hierarchy-mobile')
				.prev()
				.click();

			// should take you to that level
			cy.get('.hierarchy-mobile').find('li.level .node-card').should('have.length', 2);
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
