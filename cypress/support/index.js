// ***********************************************************
// This example support/index.js is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands.js using ES2015 syntax:
import './commands';
import '../../../frappe/cypress/support/commands' // eslint-disable-line


// Alternatively you can use CommonJS syntax:
// require('./commands')

Cypress.Cookies.defaults({
	preserve: 'sid'
});

// spy on error and warnings
Cypress.on('window:before:load', (win) => {
  cy.spy(win.console, 'error');
  cy.spy(win.console, 'log');
  cy.spy(win.console, 'warn');
});
