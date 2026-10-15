// UI scenarios for this review. Required when analysis.json lists ui_files.
// runner.mjs runs each scenario once on the base code and once on the PR code,
// against a company that holds every library and s0 document (default variant).
//
// ui.openDoc(label)               open a scenario document by its lab.reg label
// ui.openNew(doctype)             open a new form
// ui.openList(doctype, filters)   open a list view
// ui.openReport(name, filters)    open a query report; the company filter is set
// ui.setValue(fieldname, value)   set a form field and wait for its triggers
// ui.click(text)                  click a visible button or link by exact text
// ui.clickMenu(group, item)       click an item in a toolbar group, e.g. ("Create", "Payment")
// ui.save()                       save with the keyboard shortcut
// ui.capture(name)                record the page state (compared) and a screenshot (for people)
// ui.page                         the Playwright page, for anything else
//
// Capture after every step whose result the requirement or the diff cares about.
// Never read the clock, random values, or documents outside the registry.

export default [
  {
    id: "ui_s0",
    title: "<one line: what a user does on the changed screen>",
    async run(ui) {
      await ui.openDoc("s0_invoice");
      await ui.capture("opened");
    },
  },
];
