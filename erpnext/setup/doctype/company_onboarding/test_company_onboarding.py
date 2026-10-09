# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.contacts.doctype.address.address import get_default_address

from erpnext.setup.doctype.company_onboarding import company_onboarding_steps
from erpnext.setup.doctype.company_onboarding.company_onboarding import create_company_onboarding
from erpnext.setup.doctype.company_onboarding.company_onboarding_steps import HOOK_NAME, get_step_paths
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


def get_onboarding():
	create_company_onboarding(COMPANY)
	return frappe.get_doc("Company Onboarding", COMPANY)


def step_status(doc) -> dict:
	return {row.step_key.split(".")[-1]: row.status for row in doc.steps}


def extra_step(onboarding) -> dict:
	"""A step another app could add through the hook."""
	return {"title": "Extra step", "description": "", "done": False}


@contextmanager
def hooked_steps(steps_by_app: dict[str, list]):
	"""Fake the step hook of these apps; the others keep their real hook. New apps come last."""
	real_get_hooks = frappe.get_hooks
	installed = frappe.get_installed_apps()
	apps = [*installed, *(app for app in steps_by_app if app not in installed)]

	def get_hooks(hook=None, *args, **kwargs):
		if hook == HOOK_NAME and kwargs.get("app_name") in steps_by_app:
			return list(steps_by_app[kwargs["app_name"]])
		return real_get_hooks(hook, *args, **kwargs)

	with (
		patch.object(frappe, "get_installed_apps", return_value=apps),
		patch.object(frappe, "get_hooks", side_effect=get_hooks),
	):
		yield


def step_names(**steps_by_app) -> list[str]:
	"""The order of the steps, by name, with these apps' hooks."""
	with hooked_steps(steps_by_app):
		return [path.rsplit(".", 1)[-1] for path in get_step_paths()]


class TestCompanyOnboarding(ERPNextTestSuite):
	def test_new_company_gets_its_onboarding(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Onboarding Company",
				"abbr": "_TOC",
				"default_currency": "INR",
				"country": "India",
				"chart_of_accounts": "Standard",
			}
		).insert()

		doc = frappe.get_doc("Company Onboarding", company.name)
		self.assertEqual(doc.status, "In Progress")
		self.assertEqual(
			step_status(doc),
			{
				"chart_of_accounts": "Not Started",
				"opening_balances": "Not Started",
				"review": "Not Started",
				"go_live": "Not Started",
			},
		)

	def test_deleting_the_company_deletes_its_onboarding(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Onboarding Company",
				"abbr": "_TOC",
				"default_currency": "INR",
				"country": "India",
				"chart_of_accounts": "Standard",
			}
		).insert()
		self.assertTrue(frappe.db.exists("Company Onboarding", company.name))

		company.delete()
		self.assertFalse(frappe.db.exists("Company Onboarding", company.name))

	def test_a_hooked_step_shows_on_the_onboarding(self):
		extra = f"{__name__}.extra_step"
		with hooked_steps({"app_one": [{"step": extra, "after": "chart_of_accounts"}]}):
			doc = get_onboarding()
			doc.save()
		self.assertEqual(doc.steps[1].step_key, extra)
		self.assertEqual(doc.steps[1].step, "Extra step")

		# a step no app adds any more is dropped
		doc.save()
		self.assertNotIn(extra, [row.step_key for row in doc.steps])

	def test_chart_step_is_done_from_the_choice(self):
		doc = get_onboarding()
		self.assertEqual(step_status(doc)["chart_of_accounts"], "Not Started")

		doc.use_existing_chart()
		self.assertEqual(doc.chart_of_accounts_source, "Existing")
		self.assertEqual(step_status(doc)["chart_of_accounts"], "Done")

		# changing the choice asks again
		doc.change_chart_choice()
		self.assertFalse(doc.chart_of_accounts_source)
		self.assertEqual(step_status(doc)["chart_of_accounts"], "Not Started")

	def test_skip_and_bring_back(self):
		doc = get_onboarding()
		key = next(row.step_key for row in doc.steps if row.step_key.endswith("opening_balances"))

		doc.skip_step(key)
		self.assertEqual(step_status(doc)["opening_balances"], "Skipped")

		# a skipped step stays skipped when the steps are checked again
		doc.check_steps()
		self.assertEqual(step_status(doc)["opening_balances"], "Skipped")

		doc.skip_step(key, skip=0)
		self.assertEqual(step_status(doc)["opening_balances"], "Not Started")

	def test_done_step_stays_done_when_skipped(self):
		doc = get_onboarding()
		doc.use_existing_chart()
		key = next(row.step_key for row in doc.steps if row.step_key.endswith("chart_of_accounts"))

		doc.skip_step(key)
		self.assertEqual(step_status(doc)["chart_of_accounts"], "Done")

	def test_opening_balances_done_only_when_all_posted(self):
		doc = get_onboarding()
		doc.append("opening_balances", {"original_account": "Cash", "debit": 100, "status": "Posted"})
		doc.append("opening_balances", {"original_account": "Capital", "credit": 100, "status": "Draft"})
		doc.save()
		self.assertEqual(step_status(doc)["opening_balances"], "Not Started")

		doc.opening_balances[1].status = "Posted"
		doc.save()
		self.assertEqual(step_status(doc)["opening_balances"], "Done")

	def test_review_needs_temporary_opening_at_zero(self):
		doc = get_onboarding()
		doc.append("opening_balances", {"original_account": "Cash", "debit": 100, "status": "Posted"})

		with patch.object(company_onboarding_steps, "get_temporary_opening_balance", return_value=500):
			doc.save()
		self.assertEqual(step_status(doc)["review"], "Not Started")

		with patch.object(company_onboarding_steps, "get_temporary_opening_balance", return_value=0):
			doc.save()
		self.assertEqual(step_status(doc)["review"], "Done")

	def test_update_company_details(self):
		doc = get_onboarding()
		doc.update_company_details(
			{
				"tax_id": "27ABCDE1234F1Z5",
				"email": "accounts@example.com",
				"address_line1": "12 MG Road",
				"city": "Pune",
				"country": "India",
			}
		)
		self.assertEqual(frappe.db.get_value("Company", COMPANY, "tax_id"), "27ABCDE1234F1Z5")
		address = get_default_address("Company", COMPANY)
		self.assertEqual(frappe.db.get_value("Address", address, "city"), "Pune")
		self.assertTrue(frappe.db.get_value("Address", address, "is_your_company_address"))

		# the same address is updated, not a second one added
		doc.update_company_details({"address_line1": "12 MG Road", "city": "Mumbai", "country": "India"})
		self.assertEqual(get_default_address("Company", COMPANY), address)
		self.assertEqual(frappe.db.get_value("Address", address, "city"), "Mumbai")


class TestStepOrder(ERPNextTestSuite):
	"""Where steps from other apps go."""

	def test_erpnext_lists_its_steps_in_the_hook_like_any_app(self):
		self.assertEqual(
			[path.rsplit(".", 1)[-1] for path in frappe.get_hooks(HOOK_NAME, app_name="erpnext")],
			["chart_of_accounts", "opening_balances", "review", "go_live"],
		)

	def test_go_live_is_last_even_if_listed_early(self):
		go_live = "erpnext.setup.doctype.company_onboarding.company_onboarding_steps.go_live"
		self.assertEqual(
			step_names(app_one=[go_live, "app_one.steps.gst"])[-2:],
			["gst", "go_live"],
		)

	def test_erpnext_steps_alone(self):
		self.assertEqual(step_names(), ["chart_of_accounts", "opening_balances", "review", "go_live"])

	def test_step_without_a_place_goes_before_go_live(self):
		self.assertEqual(
			step_names(app_one=["app_one.steps.gst"]),
			["chart_of_accounts", "opening_balances", "review", "gst", "go_live"],
		)

	def test_before_and_after(self):
		self.assertEqual(
			step_names(
				app_one=[
					{"step": "app_one.steps.gst", "after": "chart_of_accounts"},
					{"step": "app_one.steps.bank", "before": "review"},
				]
			),
			["chart_of_accounts", "gst", "opening_balances", "bank", "review", "go_live"],
		)

	def test_same_place_keeps_install_order(self):
		self.assertEqual(
			step_names(
				app_one=[{"step": "app_one.steps.gst", "after": "chart_of_accounts"}],
				app_two=[{"step": "app_two.steps.employees", "after": "chart_of_accounts"}],
			),
			["chart_of_accounts", "gst", "employees", "opening_balances", "review", "go_live"],
		)
		self.assertEqual(
			step_names(
				app_one=[{"step": "app_one.steps.gst", "before": "review"}],
				app_two=[{"step": "app_two.steps.employees", "before": "review"}],
			),
			["chart_of_accounts", "opening_balances", "gst", "employees", "review", "go_live"],
		)

	def test_step_can_point_to_a_step_of_a_later_app(self):
		self.assertEqual(
			step_names(
				app_one=[{"step": "app_one.steps.payroll", "after": "employees"}],
				app_two=[{"step": "app_two.steps.employees", "after": "opening_balances"}],
			),
			["chart_of_accounts", "opening_balances", "employees", "payroll", "review", "go_live"],
		)

	def test_unknown_place_goes_before_go_live(self):
		self.assertEqual(
			step_names(app_one=[{"step": "app_one.steps.gst", "after": "no_such_step"}]),
			["chart_of_accounts", "opening_balances", "review", "gst", "go_live"],
		)

	def test_go_live_stays_last(self):
		self.assertEqual(
			step_names(app_one=[{"step": "app_one.steps.gst", "after": "go_live"}]),
			["chart_of_accounts", "opening_balances", "review", "gst", "go_live"],
		)

	def test_bad_entries_are_skipped(self):
		self.assertEqual(
			step_names(app_one=[42, {"after": "review"}, "app_one.steps.gst"]),
			["chart_of_accounts", "opening_balances", "review", "gst", "go_live"],
		)
