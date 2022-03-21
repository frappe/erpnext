context('Item', () => {
	before(() => {
		cy.login();
	});
	
	it('Create an item', () => {
		cy.visit(`app/item/`);
        cy.get('.primary-action').click();
        cy.get('.custom-actions > .btn').click();
        cy.get_field('item_code', 'Data').type("ITM-0018");
        cy.get_field('item_group', 'Link').type('All Item Groups');
        cy.wait(500);
        cy.get(':nth-child(2) > form > [title="is_stock_item"] > .checkbox > label > .input-area > .input-with-feedback').click();
        cy.get('.modal-footer > .standard-actions > .btn-primary').contains("Save").trigger('click', {force: true});
		cy.get_field('item_code', 'Data').should('have.value','ITM-0018');
        cy.get_field('item_group', 'Link').should('have.value', 'All Item Groups');
        cy.get_field('stock_uom', 'Link').should('have.value','Nos');
        cy.get('#page-Item > .page-head > .container > .row > .col > .standard-actions > .primary-action').click();
        cy.remove_doc('Item', 'ITM-0018');
	});
