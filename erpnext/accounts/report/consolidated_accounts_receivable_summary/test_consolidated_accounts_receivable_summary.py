# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.utils import today

from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	execute as execute_summary,
)
from erpnext.accounts.report.consolidated_accounts_receivable.test_consolidated_accounts_receivable import (
	ConsolidatedReportMixin,
)
from erpnext.accounts.report.consolidated_accounts_receivable_summary.consolidated_accounts_receivable_summary import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestConsolidatedAccountsReceivableSummary(ERPNextTestSuite, ConsolidatedReportMixin):
	def setUp(self):
		self.maxDiff = None
		# deliberately unrelated companies, no parent/child link
		self.company_a = self.create_test_company("_Test Unrelated A", "_TUNA")
		self.company_b = self.create_test_company("_Test Unrelated B", "_TUNB")
		self.create_customer("_Test Consolidation Customer")
		# the mixin would otherwise pass company=None, which Item Default rejects
		self.create_item("_Test Consolidation Item", company=self.company_a)

	def test_party_gets_a_row_per_company_plus_a_total(self):
		self.create_invoice(self.company_a, "_TUNA", 200)
		self.create_invoice(self.company_b, "_TUNB", 300)

		rows = execute(self.filters())[1]

		self.assertEqual([r.company for r in rows], [self.company_a, self.company_b, ""])
		self.assertEqual([r.party for r in rows], [self.customer, self.customer, ""])
		self.assertEqual([r.outstanding for r in rows], [200.0, 300.0, 500.0])
		self.assertEqual(rows[-1].party_type, "Total")
		self.assertTrue(rows[-1].bold)

	def test_total_matches_individual_company_summaries(self):
		self.create_invoice(self.company_a, "_TUNA", 200)
		self.create_invoice(self.company_b, "_TUNB", 300)

		total = execute(self.filters())[1][-1].outstanding
		individual = sum(self.company_outstanding(company) for company in (self.company_a, self.company_b))

		self.assertEqual(total, individual)

	def test_company_without_transactions_is_omitted(self):
		self.create_invoice(self.company_a, "_TUNA", 200)

		rows = execute(self.filters())[1]

		self.assertEqual([r.company for r in rows], [self.company_a, ""])
		self.assertEqual(rows[-1].outstanding, 200.0)

	def test_no_companies_selected_returns_nothing(self):
		self.create_invoice(self.company_a, "_TUNA", 200)

		self.assertEqual(execute(self.filters(companies=[]))[1], [])

	def test_all_parties_are_shown_when_no_party_is_selected(self):
		self.create_customer("_Test Second Consolidation Customer")
		other = self.customer
		self.create_customer("_Test Consolidation Customer")

		self.create_invoice(self.company_a, "_TUNA", 200)
		self.create_invoice(self.company_a, "_TUNA", 300, customer=other)

		filters = self.filters()
		filters.pop("party")
		parties = {r.party for r in execute(filters)[1] if r.party}

		self.assertEqual(parties, {self.customer, other})

	def test_group_by_party_carried_over_from_the_detail_report_is_ignored(self):
		# the detail report's button hands its own filters over
		self.create_invoice(self.company_a, "_TUNA", 200)

		rows = execute(self.filters(group_by_party=1))[1]

		self.assertEqual([r.outstanding for r in rows], [200.0, 200.0])

	def test_no_total_when_companies_use_different_currencies(self):
		usd = self.create_test_company("_Test Unrelated USD", "_TUNU", currency="USD")
		self.create_invoice(self.company_a, "_TUNA", 200)
		self.create_invoice(usd, "_TUNU", 300, currency="USD")

		rows = execute(self.filters(companies=[self.company_a, usd]))[1]

		self.assertEqual([r.company for r in rows], [self.company_a, usd])
		self.assertFalse(any(row.get("bold") for row in rows))

	def company_outstanding(self, company):
		filters = {"company": company, "report_date": today(), "range": "30, 60, 90, 120"}
		return sum(r.outstanding for r in execute_summary(filters)[1] if r.party == self.customer)
