"""Requirement scenarios for this review. engine.py runs them after the library, in every company.

lab.ctx: company, abbr, currency, foreign_currency, receivable, payable, income, expense,
         cash, bank, tax, receivable_eur (in foreign_currency), cost_center, warehouse,
         customer, customer_eur, supplier, service_item, stock_item.
         The variant's settings are already applied.
lab.reg(label, doc)       register a document; its snapshot key is the label (no dots).
lab.get(label)            the registered document.
lab.attempt(label, fn)    run fn; record "ok" or the error under outcomes.<label>.

Post on DATE (or day(n)). Pass every account, currency and conversion_rate.
Never read today's date, a random value, or a site record outside lab.ctx.
"""

import frappe
from library import scenario
from pr_ledger import DATE, day


def s0_build(lab):
	"""The requirement's Repro, with the reporter's data. One function per reported case."""
	raise NotImplementedError("write the Repro")


def s0_legacy(lab):
	"""What happens later to the Repro's documents (cancel, return, pay), if the requirement involves it."""


# Ids must not clash with library.SCENARIOS. The title appears in the report.
SCENARIOS = [
	scenario(
		"s0", "<one line: the reported case, in the reporter's words>", ["requirement"], s0_build, s0_legacy
	)
]


def reports(ctx):
	"""Extra reports from the blast radius: {label: (report_name, filters)}. Use DATE-based filters."""
	return {}
