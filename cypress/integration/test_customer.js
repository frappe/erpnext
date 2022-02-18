
context('Customer', () => {
	before(() => {
		cy.login();
	});
	it('Check Customer Group', () => {
		cy.visit(`app/customer/`);
		cy.get('.primary-action').click();
		cy.wait(500);
		cy.get('.custom-actions > .btn').click();
		cy.get_field('customer_group', 'Link').should('have.value', 'All Customer Groups');
	});
});
