
context('Item Creation', () => {
	before(() => {
		cy.login();
	});

	it('Create Item', () => {
		cy.visit(`app/item/`);
		cy.click_listview_primary_button('Add Item');
		cy.findByRole('button', {name: /Edit in full page/}).click();
		cy.get_field('item_code', 'Data').type('Solid Wood Chair Set');
		cy.get_field('item_name', 'Data').should('have.value', 'Solid Wood Chair Set');
		cy.fill_field('item_group', 'All Item Groups', 'Link');
		cy.get_field('valuation_rate', 'Data').clear().type('8000');
		cy.get_field('stock_uom', 'Link').clear().type('Nos');
		cy.findByRole('button', {name: 'Save'}).click();
	});

	it('Check item form values', () => {
		cy.get('.page-title').should('contain', 'Solid Wood Chair Set');
		cy.get('.page-title').should('contain', 'Enabled');
		cy.get_field('item_name', 'Data').should('have.value', 'Solid Wood Chair Set');
		cy.get_field('is_stock_item', 'checkbox').should('be.checked');
		cy.get_field('valuation_rate', 'Data').should('have.value', '8,000.00');
	});

	after(() => {
		cy.remove_doc('Item', 'Solid Wood Chair Set');
	});
});

