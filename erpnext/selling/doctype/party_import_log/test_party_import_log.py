# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import csv
import json
import tempfile
from typing import ClassVar
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from erpnext.selling.doctype.party_import_log.column_mapper import ColumnMapper, normalize
from erpnext.selling.doctype.party_import_log.dependency_resolver import (
	DependencyAnalyzer,
	DependencyResolver,
	count_values,
	invert_mappings,
	source_for_target,
	split_tree_path,
)
from erpnext.selling.doctype.party_import_log.file_reader import FileReader
from erpnext.selling.doctype.party_import_log.import_runner import ImportRunner
from erpnext.selling.doctype.party_import_log.party_creator import PartyCreator
from erpnext.selling.doctype.party_import_log.party_import_log import (
	delete_mapping_template,
	list_mapping_templates,
	load_mapping_template,
	save_mapping_template,
)
from erpnext.selling.doctype.party_import_log.schema import (
	CUSTOMER,
	SUPPLIER,
	dependency_fields_for,
	target_fields_for,
)
from erpnext.selling.doctype.party_import_log.templates import (
	GENERIC,
	HUBSPOT,
	QUICKBOOKS,
	SALESFORCE,
	SOURCE_FORMATS,
	TALLY,
	ZOHO,
	filename_suffix_for,
	get_template_columns,
	get_template_mappings,
)


class TestSchema(UnitTestCase):
	def test_target_fields_exactly_one_required_identity(self):
		fields = target_fields_for(CUSTOMER)
		required = [f for f in fields if f[3] is True]
		self.assertEqual(len(required), 1)
		self.assertEqual(required[0][0], "customer_name")

	def test_customer_group_is_tree_dependency(self):
		dep = dependency_fields_for(CUSTOMER)
		self.assertIn("customer_group", dep)
		self.assertEqual(dep["customer_group"], ("Customer Group", True))

	def test_supplier_has_no_territory_dependency(self):
		self.assertNotIn("territory", dependency_fields_for(SUPPLIER))


class TestColumnMapper(UnitTestCase):
	def setUp(self):
		self.mapper = ColumnMapper(target_fields_for(CUSTOMER))

	def test_synonyms_map_common_aliases(self):
		result = self.mapper.suggest(["GSTIN", "Company Name", "Email"])
		self.assertEqual(result["GSTIN"], "tax_id")
		self.assertEqual(result["Company Name"], "customer_name")
		self.assertEqual(result["Email"], "primary_email")

	def test_direct_match_on_field_label(self):
		self.assertEqual(self.mapper.suggest(["Tax ID"]).get("Tax ID"), "tax_id")

	def test_unrecognized_column_excluded(self):
		self.assertNotIn("XYZ_UNKNOWN", self.mapper.suggest(["XYZ_UNKNOWN"]))

	def test_normalize_strips_specials_and_lowercases(self):
		self.assertEqual(normalize("Tax-ID!"), "taxid")
		self.assertEqual(normalize("  ZIP Code  "), "zipcode")
		self.assertEqual(normalize(""), "")

	def test_substring_match_pulls_in_natural_form_headers(self):
		# "Customer Address" should map to billing_address_line1 via the
		# substring rule (synonym "address" is contained in normalized source).
		result = self.mapper.suggest(["Customer Address"])
		self.assertEqual(result.get("Customer Address"), "billing_address_line1")

	def test_fuzzy_match_tolerates_typos(self):
		# "Custmer Name" — typo — should still map to customer_name via the
		# SequenceMatcher fallback.
		result = self.mapper.suggest(["Custmer Name"])
		self.assertEqual(result.get("Custmer Name"), "customer_name")

	def test_greedy_assignment_prevents_duplicate_targets(self):
		# Both columns could map to customer_name; the synonym match
		# ("Company Name") outranks the fuzzy one, so the noisier column
		# is left unassigned for manual mapping.
		result = self.mapper.suggest(["Company Name", "Cust Nam"])
		self.assertEqual(result.get("Company Name"), "customer_name")
		self.assertNotIn("Cust Nam", result)


class TestTallyTemplate(UnitTestCase):
	"""Tally pre-mapped template — synonyms generic ColumnMapper doesn't know about."""

	def test_tally_customer_template_maps_ledger_and_under(self):
		template = get_template_mappings(TALLY, CUSTOMER)
		self.assertEqual(template["ledgername"], "customer_name")
		self.assertEqual(template["mailingname"], "customer_name")
		self.assertEqual(template["under"], "customer_group")
		self.assertEqual(template["gstinuin"], "tax_id")
		self.assertEqual(template["telephone"], "primary_phone")

	def test_tally_supplier_template_swaps_party_type(self):
		template = get_template_mappings(TALLY, SUPPLIER)
		self.assertEqual(template["ledgername"], "supplier_name")
		self.assertEqual(template["under"], "supplier_group")

	def test_generic_returns_empty_template(self):
		self.assertEqual(get_template_mappings(GENERIC, CUSTOMER), {})

	def test_mapper_applies_tally_template(self):
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(TALLY, CUSTOMER),
		)
		result = mapper.suggest(["Ledger Name", "GSTIN/UIN", "Under", "Telephone"])
		self.assertEqual(result["Ledger Name"], "customer_name")
		self.assertEqual(result["GSTIN/UIN"], "tax_id")
		self.assertEqual(result["Under"], "customer_group")
		self.assertEqual(result["Telephone"], "primary_phone")

	def test_tally_customer_columns_start_with_ledger_and_under(self):
		columns = get_template_columns(TALLY, CUSTOMER)
		self.assertEqual(columns[0], ("Ledger Name", "customer_name"))
		self.assertEqual(columns[1], ("Under", "customer_group"))
		self.assertIn(("GSTIN/UIN", "tax_id"), columns)

	def test_tally_supplier_columns_swap_party_fields(self):
		columns = get_template_columns(TALLY, SUPPLIER)
		self.assertEqual(columns[0], ("Ledger Name", "supplier_name"))
		self.assertEqual(columns[1], ("Under", "supplier_group"))

	def test_generic_columns_return_none(self):
		self.assertIsNone(get_template_columns(GENERIC, CUSTOMER))

	def test_download_template_uses_tally_headers(self):
		"""End-to-end: download_template for Tally produces a CSV with Tally-styled headers."""
		from erpnext.selling.doctype.party_import_log import party_import_log as module

		frappe.response.clear() if hasattr(frappe.response, "clear") else frappe.response.update({})
		module.download_template(party_type=CUSTOMER, with_sample=0, source_format=TALLY)
		content = frappe.response["filecontent"]
		header_line = content.splitlines()[0]
		self.assertIn("Ledger Name", header_line)
		self.assertIn("Under", header_line)
		self.assertIn("GSTIN/UIN", header_line)
		# No raw fieldnames in the Tally header line
		self.assertNotIn("customer_name", header_line)
		self.assertNotIn("customer_group", header_line)
		# Filename suffix encodes the format
		self.assertIn("_tally", frappe.response["filename"])

	def test_download_template_with_sample_fills_tally_columns(self):
		from erpnext.selling.doctype.party_import_log import party_import_log as module

		module.download_template(party_type=CUSTOMER, with_sample=1, source_format=TALLY)
		content = frappe.response["filecontent"]
		lines = content.splitlines()
		# header + 3 customer samples
		self.assertEqual(len(lines), 4)
		# First sample row's first column should be the Acme Corp name (Ledger Name → customer_name)
		self.assertTrue(lines[1].startswith("Acme Corp,"))


class TestQuickBooksTemplate(UnitTestCase):
	"""QuickBooks pre-mapped template — QBO Customer/Vendor export shape."""

	def test_customer_template_resolves_party_specific_synonyms(self):
		template = get_template_mappings(QUICKBOOKS, CUSTOMER)
		self.assertEqual(template["customer"], "customer_name")
		self.assertEqual(template["displayname"], "customer_name")
		self.assertEqual(template["printoncheckas"], "customer_name")
		self.assertEqual(template["customertype"], "customer_group")
		self.assertEqual(template["taxresaleno"], "tax_id")

	def test_supplier_template_swaps_party_type(self):
		template = get_template_mappings(QUICKBOOKS, SUPPLIER)
		self.assertEqual(template["vendor"], "supplier_name")
		self.assertEqual(template["customer"], "supplier_name")
		self.assertEqual(template["vendortype"], "supplier_group")

	def test_phone_and_mobile_route_to_distinct_targets(self):
		# In QB, "Phone" is the landline and "Mobile" is the cell — the generic
		# dict would collide both onto primary_mobile.
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(QUICKBOOKS, CUSTOMER),
		)
		result = mapper.suggest(["Phone", "Mobile"])
		self.assertEqual(result["Phone"], "primary_phone")
		self.assertEqual(result["Mobile"], "primary_mobile")

	def test_mapper_recognises_quickbooks_headers(self):
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(QUICKBOOKS, CUSTOMER),
		)
		result = mapper.suggest(["Customer", "Customer Type", "Tax Resale No", "Billing Postal Code"])
		self.assertEqual(result["Customer"], "customer_name")
		self.assertEqual(result["Customer Type"], "customer_group")
		self.assertEqual(result["Tax Resale No"], "tax_id")
		self.assertEqual(result["Billing Postal Code"], "billing_pincode")

	def test_columns_lead_with_party_fields(self):
		columns = get_template_columns(QUICKBOOKS, CUSTOMER)
		self.assertEqual(columns[0], ("Customer", "customer_name"))
		self.assertEqual(columns[1], ("Customer Type", "customer_group"))
		self.assertIn(("Tax Resale No", "tax_id"), columns)

	def test_supplier_columns_swap_party_fields(self):
		columns = get_template_columns(QUICKBOOKS, SUPPLIER)
		self.assertEqual(columns[0], ("Customer", "supplier_name"))
		self.assertEqual(columns[1], ("Customer Type", "supplier_group"))


class TestZohoTemplate(UnitTestCase):
	"""Zoho pre-mapped template — Zoho Books / Zoho CRM contact export shape."""

	def test_customer_template_resolves_party_specific_synonyms(self):
		template = get_template_mappings(ZOHO, CUSTOMER)
		self.assertEqual(template["displayname"], "customer_name")
		self.assertEqual(template["contactname"], "customer_name")
		self.assertEqual(template["customersubtype"], "customer_group")

	def test_supplier_template_swaps_party_type(self):
		template = get_template_mappings(ZOHO, SUPPLIER)
		self.assertEqual(template["displayname"], "supplier_name")
		self.assertEqual(template["vendorsubtype"], "supplier_group")

	def test_verbose_tax_id_headers_map_correctly(self):
		# Zoho's verbose "GST Identification Number (GSTIN)" and
		# "PAN Identification Number (PAN)" both belong on tax_id.
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(ZOHO, CUSTOMER),
		)
		# Only one can win the greedy assignment, but both should be in the
		# template synonyms so the loser can be hand-mapped without confusion.
		template = get_template_mappings(ZOHO, CUSTOMER)
		self.assertEqual(template["gstidentificationnumbergstin"], "tax_id")
		self.assertEqual(template["panidentificationnumberpan"], "tax_id")
		# At least one of them auto-maps to tax_id when present alone.
		result = mapper.suggest(["GST Identification Number (GSTIN)"])
		self.assertEqual(result["GST Identification Number (GSTIN)"], "tax_id")

	def test_split_address_columns_map_to_line1_and_line2(self):
		# Zoho splits address as "Billing Address" (line 1) and "Billing Street2" (line 2).
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(ZOHO, CUSTOMER),
		)
		result = mapper.suggest(["Billing Address", "Billing Street2", "Billing Code"])
		self.assertEqual(result["Billing Address"], "billing_address_line1")
		self.assertEqual(result["Billing Street2"], "billing_address_line2")
		self.assertEqual(result["Billing Code"], "billing_pincode")

	def test_columns_lead_with_party_fields(self):
		columns = get_template_columns(ZOHO, CUSTOMER)
		self.assertEqual(columns[0], ("Display Name", "customer_name"))
		self.assertEqual(columns[1], ("Customer Sub Type", "customer_group"))
		self.assertIn(("EmailID", "primary_email"), columns)

	def test_supplier_columns_swap_party_fields(self):
		columns = get_template_columns(ZOHO, SUPPLIER)
		self.assertEqual(columns[0], ("Display Name", "supplier_name"))
		self.assertEqual(columns[1], ("Customer Sub Type", "supplier_group"))


class TestHubSpotTemplate(UnitTestCase):
	"""HubSpot pre-mapped template — companies / contacts export shape."""

	def test_customer_template_resolves_party_specific_synonyms(self):
		template = get_template_mappings(HUBSPOT, CUSTOMER)
		self.assertEqual(template["companyname"], "customer_name")
		self.assertEqual(template["company"], "customer_name")
		self.assertEqual(template["contactname"], "customer_name")
		self.assertEqual(template["lifecyclestage"], "customer_group")

	def test_supplier_template_swaps_party_type(self):
		template = get_template_mappings(HUBSPOT, SUPPLIER)
		self.assertEqual(template["companyname"], "supplier_name")
		self.assertEqual(template["lifecyclestage"], "supplier_group")

	def test_phone_and_mobile_route_to_distinct_targets(self):
		# HubSpot "Phone Number" is the main line; "Mobile Phone Number" is the cell.
		# The generic SYNONYMS would map both "phonenumber" to primary_mobile.
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(HUBSPOT, CUSTOMER),
		)
		result = mapper.suggest(["Phone Number", "Mobile Phone Number"])
		self.assertEqual(result["Phone Number"], "primary_phone")
		self.assertEqual(result["Mobile Phone Number"], "primary_mobile")

	def test_mapper_recognises_hubspot_headers(self):
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(HUBSPOT, CUSTOMER),
		)
		result = mapper.suggest(["Company Name", "Lifecycle Stage", "Street Address", "State/Region"])
		self.assertEqual(result["Company Name"], "customer_name")
		self.assertEqual(result["Lifecycle Stage"], "customer_group")
		self.assertEqual(result["Street Address"], "billing_address_line1")
		self.assertEqual(result["State/Region"], "billing_state")

	def test_columns_lead_with_party_fields(self):
		columns = get_template_columns(HUBSPOT, CUSTOMER)
		self.assertEqual(columns[0], ("Company Name", "customer_name"))
		self.assertEqual(columns[1], ("Lifecycle Stage", "customer_group"))
		self.assertIn(("Phone Number", "primary_phone"), columns)
		self.assertIn(("Street Address", "billing_address_line1"), columns)

	def test_supplier_columns_swap_party_fields(self):
		columns = get_template_columns(HUBSPOT, SUPPLIER)
		self.assertEqual(columns[0], ("Company Name", "supplier_name"))
		self.assertEqual(columns[1], ("Lifecycle Stage", "supplier_group"))


class TestSalesforceTemplate(UnitTestCase):
	"""Salesforce pre-mapped template — account / contact export shape."""

	def test_customer_template_resolves_party_specific_synonyms(self):
		template = get_template_mappings(SALESFORCE, CUSTOMER)
		self.assertEqual(template["accountname"], "customer_name")
		self.assertEqual(template["type"], "customer_group")
		self.assertEqual(template["accounttype"], "customer_group")

	def test_supplier_template_swaps_party_type(self):
		template = get_template_mappings(SALESFORCE, SUPPLIER)
		self.assertEqual(template["accountname"], "supplier_name")
		self.assertEqual(template["type"], "supplier_group")

	def test_phone_routes_to_primary_phone_not_mobile(self):
		# Salesforce "Phone" is the business landline; the generic synonym
		# would map it to primary_mobile.
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(SALESFORCE, CUSTOMER),
		)
		result = mapper.suggest(["Phone", "Mobile"])
		self.assertEqual(result["Phone"], "primary_phone")
		self.assertEqual(result["Mobile"], "primary_mobile")

	def test_billing_address_headers_map_correctly(self):
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(SALESFORCE, CUSTOMER),
		)
		result = mapper.suggest(
			[
				"Billing Street",
				"Billing City",
				"Billing State/Province",
				"Billing Zip/Postal Code",
				"Billing Country",
			]
		)
		self.assertEqual(result["Billing Street"], "billing_address_line1")
		self.assertEqual(result["Billing City"], "billing_city")
		self.assertEqual(result["Billing State/Province"], "billing_state")
		self.assertEqual(result["Billing Zip/Postal Code"], "billing_pincode")
		self.assertEqual(result["Billing Country"], "billing_country")

	def test_mailing_address_headers_map_to_billing_fields(self):
		# Salesforce Contact export uses "Mailing" prefix for the primary address.
		mapper = ColumnMapper(
			target_fields_for(CUSTOMER),
			template_synonyms=get_template_mappings(SALESFORCE, CUSTOMER),
		)
		result = mapper.suggest(["Mailing Street", "Mailing City", "Mailing Country"])
		self.assertEqual(result["Mailing Street"], "billing_address_line1")
		self.assertEqual(result["Mailing City"], "billing_city")
		self.assertEqual(result["Mailing Country"], "billing_country")

	def test_currency_iso_code_maps_to_default_currency(self):
		template = get_template_mappings(SALESFORCE, CUSTOMER)
		self.assertEqual(template["currencyisocode"], "default_currency")

	def test_columns_lead_with_party_fields(self):
		columns = get_template_columns(SALESFORCE, CUSTOMER)
		self.assertEqual(columns[0], ("Account Name", "customer_name"))
		self.assertEqual(columns[1], ("Type", "customer_group"))
		self.assertIn(("Billing Street", "billing_address_line1"), columns)
		self.assertIn(("Shipping Street", "shipping_address_line1"), columns)

	def test_supplier_columns_swap_party_fields(self):
		columns = get_template_columns(SALESFORCE, SUPPLIER)
		self.assertEqual(columns[0], ("Account Name", "supplier_name"))
		self.assertEqual(columns[1], ("Type", "supplier_group"))


class TestSourceFormatRegistry(UnitTestCase):
	"""Cross-cutting checks that hold for every non-generic template."""

	NON_GENERIC = (TALLY, QUICKBOOKS, ZOHO, HUBSPOT, SALESFORCE)

	def test_all_known_formats_listed(self):
		self.assertEqual(SOURCE_FORMATS, (GENERIC, TALLY, QUICKBOOKS, ZOHO, HUBSPOT, SALESFORCE))

	def test_filename_suffix_per_format(self):
		self.assertEqual(filename_suffix_for(GENERIC), "")
		self.assertEqual(filename_suffix_for("unknown"), "")
		self.assertEqual(filename_suffix_for(TALLY), "_tally")
		self.assertEqual(filename_suffix_for(QUICKBOOKS), "_quickbooks")
		self.assertEqual(filename_suffix_for(ZOHO), "_zoho")
		self.assertEqual(filename_suffix_for(HUBSPOT), "_hubspot")
		self.assertEqual(filename_suffix_for(SALESFORCE), "_salesforce")

	def test_download_template_uses_format_specific_suffix(self):
		from erpnext.selling.doctype.party_import_log import party_import_log as module

		for source_format in self.NON_GENERIC:
			with self.subTest(source_format=source_format):
				module.download_template(party_type=CUSTOMER, source_format=source_format)
				self.assertIn(filename_suffix_for(source_format), frappe.response["filename"])

	def test_every_template_resolves_name_and_group_sentinels(self):
		# No "__name__" / "__group__" placeholder should leak through into the
		# resolved column list — a bug here would crash the CSV writer.
		for source_format in self.NON_GENERIC:
			for party_type in (CUSTOMER, SUPPLIER):
				with self.subTest(source_format=source_format, party_type=party_type):
					columns = get_template_columns(source_format, party_type)
					targets = [target for _header, target in columns]
					self.assertNotIn("__name__", targets)
					self.assertNotIn("__group__", targets)

	def test_template_columns_dont_repeat_target_fields(self):
		# Two columns mapping to the same target would silently drop one
		# during the column-mapping greedy assignment.
		for source_format in self.NON_GENERIC:
			for party_type in (CUSTOMER, SUPPLIER):
				with self.subTest(source_format=source_format, party_type=party_type):
					columns = get_template_columns(source_format, party_type)
					targets = [target for _header, target in columns]
					self.assertEqual(len(targets), len(set(targets)))


class TestDependencyResolver(UnitTestCase):
	def _resolver(self, values):
		return DependencyResolver({"Customer Group": {"values": values}})

	def test_all_resolution_actions(self):
		resolver = DependencyResolver(
			{
				"Customer Group": {
					"values": [
						{"value": "Keep", "action": "use"},
						{"value": "Old", "action": "map", "map_to": "New"},
						{"value": "Junk", "action": "skip"},
						{"value": "Parent / Leaf", "action": "create"},
					]
				}
			}
		)
		self.assertEqual(resolver.resolve("Customer Group", "Keep"), "Keep")
		self.assertEqual(resolver.resolve("Customer Group", "Old"), "New")
		self.assertIsNone(resolver.resolve("Customer Group", "Junk"))
		self.assertEqual(resolver.resolve("Customer Group", "Parent / Leaf"), "Leaf")

	def test_missing_or_empty_value_returns_none(self):
		resolver = DependencyResolver({})
		self.assertIsNone(resolver.resolve("Customer Group", ""))
		self.assertIsNone(resolver.resolve("Customer Group", None))

	def test_masters_to_create_groups_by_doctype(self):
		resolver = DependencyResolver(
			{
				"Customer Group": {
					"values": [
						{"value": "New Group", "action": "create"},
						{"value": "Existing", "action": "use"},
					]
				},
				"Territory": {"values": [{"value": "New Territory", "action": "create"}]},
			}
		)
		self.assertEqual(
			resolver.masters_to_create(),
			{"Customer Group": ["New Group"], "Territory": ["New Territory"]},
		)

	def test_should_skip_row(self):
		resolver = self._resolver([{"value": "Junk", "action": "skip"}])
		dep_fields = dependency_fields_for(CUSTOMER)
		self.assertTrue(resolver.should_skip_row({"grp": "Junk"}, {"grp": "customer_group"}, dep_fields))
		self.assertFalse(resolver.should_skip_row({"x": "Junk"}, {}, dep_fields))


class TestDependencyAnalyzerSuggest(UnitTestCase):
	"""Master-record suggestions: exact, substring, fuzzy, and threshold rejection."""

	def _analyzer(self, records: list[str]) -> DependencyAnalyzer:
		analyzer = DependencyAnalyzer({"customer_group": ("Customer Group", True)}, {})
		analyzer._cache["Customer Group"] = records
		return analyzer

	def test_exact_normalized_match_wins(self):
		analyzer = self._analyzer(["Retail Customers", "Wholesale", "Distributor"])
		self.assertEqual(analyzer._suggest_match("Customer Group", "retail customers"), "Retail Customers")

	def test_substring_match_picks_closest_length(self):
		# "Retail" is a substring of both — the closer-length one wins via scoring.
		analyzer = self._analyzer(["Retail Customers - Premium", "Retail"])
		self.assertEqual(analyzer._suggest_match("Customer Group", "Retail"), "Retail")

	def test_fuzzy_match_tolerates_typos(self):
		analyzer = self._analyzer(["Retail Customer", "Wholesale", "Distributor"])
		self.assertEqual(analyzer._suggest_match("Customer Group", "Reatil Customer"), "Retail Customer")

	def test_unrelated_value_returns_none(self):
		analyzer = self._analyzer(["Retail Customer", "Wholesale"])
		self.assertIsNone(analyzer._suggest_match("Customer Group", "Government Agency"))


class TestDependencyResolverUtils(UnitTestCase):
	def test_invert_mappings(self):
		result = invert_mappings({"col_a": "customer_name", "col_b": "", "col_c": "territory"})
		self.assertEqual(result, {"customer_name": "col_a", "territory": "col_c"})
		self.assertNotIn("", result)

	def test_source_for_target(self):
		self.assertEqual(source_for_target({"a": "x", "b": "y"}, "y"), "b")
		self.assertIsNone(source_for_target({"a": "x"}, "missing"))

	def test_count_values_sorted_descending_ignores_blank(self):
		rows = [{"c": "A"}, {"c": "B"}, {"c": "A"}, {"c": "A"}, {"c": ""}]
		result = count_values(rows, "c")
		self.assertEqual(result[0], ("A", 3))
		self.assertEqual(result[1], ("B", 1))
		self.assertNotIn(("", 1), result)

	def test_split_tree_path(self):
		self.assertEqual(split_tree_path("Parent / Child / Leaf"), ["Parent", "Child", "Leaf"])
		self.assertEqual(split_tree_path(""), [])
		self.assertEqual(split_tree_path("/  /"), [])
		self.assertEqual(split_tree_path("Standalone"), ["Standalone"])


class TestMarkFailed(UnitTestCase):
	"""``_mark_failed`` must persist via db writes so a broken lifecycle can't mask the error."""

	def test_writes_status_and_error_without_calling_save(self):
		from erpnext.selling.doctype.party_import_log import party_import_log as module

		doc = MagicMock(name="DocStub")
		doc.name = "PIL-TEST"

		with patch.object(module, "frappe") as mock_frappe:
			mock_frappe.db.get_value.return_value = '[{"row": 5, "message": "earlier"}]'
			module._mark_failed(doc, Exception("boom"))

			doc.save.assert_not_called()
			doc.reload.assert_not_called()

			call_args = mock_frappe.db.set_value.call_args
			self.assertEqual(call_args[0][0], module.DOCTYPE)
			self.assertEqual(call_args[0][1], "PIL-TEST")
			values = call_args[0][2]
			self.assertEqual(values["status"], "Failed")
			errors = json.loads(values["error_log"])
			self.assertEqual(errors[-1], {"row": None, "message": "boom"})
			self.assertEqual(errors[0], {"row": 5, "message": "earlier"})
			mock_frappe.db.commit.assert_called_once()

	def test_db_failure_is_swallowed_and_logged(self):
		"""Even if the DB write itself fails, the original exception must still propagate from run_import."""
		from erpnext.selling.doctype.party_import_log import party_import_log as module

		doc = MagicMock()
		doc.name = "PIL-BROKEN"

		with patch.object(module, "frappe") as mock_frappe:
			mock_frappe.db.get_value.side_effect = Exception("db down")
			module._mark_failed(doc, Exception("original"))
			mock_frappe.log_error.assert_called_once()


class TestFileReader(UnitTestCase):
	def _write_csv(self, rows: list[dict]) -> str:
		with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
			writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
			writer.writeheader()
			writer.writerows(rows)
			return f.name

	def test_csv_read_returns_rows_keyed_by_header(self):
		path = self._write_csv([{"name": "Acme", "city": "Delhi"}])
		with patch("erpnext.selling.doctype.party_import_log.file_reader.get_file_path", return_value=path):
			rows = FileReader(path).read()
		self.assertEqual(rows, [{"name": "Acme", "city": "Delhi"}])

	def test_csv_strips_utf8_bom(self):
		with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
			f.write(b"\xef\xbb\xbfcustomer_name,city\nAcme Corp,Delhi\n")
			path = f.name
		with patch("erpnext.selling.doctype.party_import_log.file_reader.get_file_path", return_value=path):
			rows = FileReader(path).read()
		self.assertEqual(rows[0]["customer_name"], "Acme Corp")

	def test_unsupported_extension_raises(self):
		with patch(
			"erpnext.selling.doctype.party_import_log.file_reader.get_file_path",
			return_value="/some/file.txt",
		):
			with self.assertRaises(Exception):
				FileReader("/some/file.txt").read()

	def test_multi_sheet_xlsx_appends_warning(self):
		fake_ws = MagicMock()
		fake_ws.title = "Sheet1"
		fake_wb = MagicMock()
		fake_wb.sheetnames = ["Sheet1", "Sheet2"]
		fake_wb.active = fake_ws
		warnings = []
		FileReader("/f.xlsx", warnings=warnings)._warn_if_multi_sheet(fake_wb)
		self.assertEqual(len(warnings), 1)
		self.assertIn("Sheet2", warnings[0])


class TestImportRunnerDryRun(UnitTestCase):
	def _make_doc(self, resolutions=None):
		doc = MagicMock()
		doc.party_type = "Customer"
		doc.conflict_policy = "Update Existing"
		doc.get_mappings.return_value = {
			"customer_name": "customer_name",
			"customer_group": "customer_group",
		}
		doc.get_resolutions.return_value = resolutions or {}
		return doc

	def test_dry_run_classifies_new_existing_and_errors(self):
		doc = self._make_doc()
		rows = [
			{"customer_name": "__NonExistent__", "customer_group": "Commercial"},
			{"customer_name": "", "customer_group": "Commercial"},
		]
		result = ImportRunner(doc).dry_run(rows)
		self.assertEqual(result["to_create"], 1)
		self.assertEqual(result["error_count"], 1)

	def test_dry_run_skip_action_counts_as_skip(self):
		doc = self._make_doc({"Customer Group": {"values": [{"value": "Junk", "action": "skip"}]}})
		rows = [{"customer_name": "SomeCustomer", "customer_group": "Junk"}]
		self.assertEqual(ImportRunner(doc).dry_run(rows)["to_skip"], 1)

	def test_dry_run_returns_masters_to_create(self):
		doc = MagicMock()
		doc.party_type = "Customer"
		doc.conflict_policy = "Update Existing"
		doc.get_mappings.return_value = {"customer_group": "customer_group"}
		doc.get_resolutions.return_value = {
			"Customer Group": {"values": [{"value": "BrandNew", "action": "create"}]}
		}
		result = ImportRunner(doc).dry_run([])
		self.assertIn("BrandNew", result["masters_to_create"].get("Customer Group", []))

	def _runner(self, mappings, rows_overrides=None):
		doc = MagicMock()
		doc.party_type = "Customer"
		doc.conflict_policy = "Skip"
		doc.get_mappings.return_value = mappings
		doc.get_resolutions.return_value = {}
		doc.row_overrides = json.dumps(rows_overrides or {})
		return ImportRunner(doc)

	def test_dry_run_marks_editable_when_under_threshold(self):
		runner = self._runner({"name": "customer_name"})
		# 3 rows, all missing customer_name → 3 errors, well under threshold
		result = runner.dry_run([{"name": ""}, {"name": ""}, {"name": ""}])
		self.assertTrue(result["editable"])
		self.assertEqual(result["error_count"], 3)
		self.assertIn("inline_edit_limit", result)

	def test_dry_run_marks_not_editable_when_over_threshold(self):
		runner = self._runner({"name": "customer_name"})
		rows = [{"name": ""} for _ in range(60)]
		result = runner.dry_run(rows)
		self.assertFalse(result["editable"])
		self.assertEqual(result["error_count"], 60)
		# When not editable, only DRY_RUN_ERROR_LIMIT (20) errors are sent back
		self.assertEqual(len(result["errors"]), 20)

	def test_dry_run_errors_carry_effective_values(self):
		runner = self._runner({"name": "customer_name", "email": "primary_email"})
		result = runner.dry_run([{"name": "", "email": "x@y"}])
		err = result["errors"][0]
		self.assertEqual(err["values"]["primary_email"], "x@y")
		self.assertEqual(err["values"]["customer_name"], "")

	def test_dry_run_applies_row_override_to_name(self):
		runner = self._runner(
			{"name": "customer_name"}, rows_overrides={"2": {"customer_name": "Fixed Name"}}
		)
		dry_run_result = runner.dry_run([{"name": ""}])
		# Override fills in the missing name → no error, classified as create or update
		self.assertEqual(dry_run_result["error_count"], 0)
		# Effective value reflects the override
		# (verify via _effective_values directly since errors list is empty here)
		values = runner._effective_values({"name": ""}, 2)
		self.assertEqual(values["customer_name"], "Fixed Name")


class TestPartyCreatorIntegration(UnitTestCase):
	TEST_CUSTOMER = "_PI Test Customer"
	TEST_EMAIL = "pi_test_contact@example.com"

	def tearDown(self):
		for name in frappe.get_all("Customer", filters={"customer_name": self.TEST_CUSTOMER}, pluck="name"):
			for link in frappe.get_all(
				"Dynamic Link", filters={"link_doctype": "Customer", "link_name": name}, fields=["parent"]
			):
				frappe.delete_doc("Address", link.parent, ignore_permissions=True, force=True)
			frappe.delete_doc("Customer", name, ignore_permissions=True, force=True)
		for name in frappe.get_all("Contact", filters={"email_id": self.TEST_EMAIL}, pluck="name"):
			frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)

	def _creator(self, mappings=None):
		return PartyCreator(
			CUSTOMER,
			mappings
			or {
				"customer_name": "customer_name",
				"customer_group": "customer_group",
				"primary_email": "primary_email",
				"billing_city": "billing_city",
				"billing_country": "billing_country",
				"website": "website",
			},
			DependencyResolver({}),
		)

	def _base_row(self, **kwargs):
		return {"customer_name": self.TEST_CUSTOMER, "customer_group": "Commercial", **kwargs}

	def test_create_inserts_customer_with_defaults(self):
		party_name = self._creator().create(self._base_row())
		doc = frappe.get_doc("Customer", party_name)
		self.assertTrue(frappe.db.exists("Customer", party_name))
		self.assertEqual(doc.customer_type, "Company")

	def test_create_links_contact_to_customer(self):
		self._creator().create(self._base_row(primary_email=self.TEST_EMAIL))
		contacts = frappe.get_all(
			"Contact",
			filters=[["Dynamic Link", "link_doctype", "=", "Customer"]],
			pluck="name",
		)
		self.assertTrue(len(contacts) > 0)

	def test_update_existing_and_empty_only_policies(self):
		self._creator().create(self._base_row(website="https://original.example"))
		existing = frappe.db.exists("Customer", {"customer_name": self.TEST_CUSTOMER})

		self._creator().update(existing, self._base_row(website="https://new.example"), "Update Existing")
		self.assertEqual(frappe.db.get_value("Customer", existing, "website"), "https://new.example")

		self._creator().update(
			existing, self._base_row(website="https://ignored.example"), "Update Empty Fields Only"
		)
		self.assertEqual(frappe.db.get_value("Customer", existing, "website"), "https://new.example")

	def test_row_to_value_map_excludes_skipped_resolution(self):
		resolver = DependencyResolver(
			{"Customer Group": {"values": [{"value": "Ignored", "action": "skip"}]}}
		)
		creator = PartyCreator(CUSTOMER, {"customer_group": "customer_group"}, resolver)
		self.assertNotIn("customer_group", creator.row_to_value_map({"customer_group": "Ignored"}))

	def test_same_address_line1_creates_single_address(self):
		"""Identical billing/shipping address_line1 → one Address with both flags set."""
		address_mappings = {
			"customer_name": "customer_name",
			"customer_group": "customer_group",
			"billing_address_line1": "billing_address_line1",
			"billing_city": "billing_city",
			"billing_country": "billing_country",
			"shipping_address_line1": "shipping_address_line1",
			"shipping_city": "shipping_city",
			"shipping_country": "shipping_country",
		}
		creator = PartyCreator(CUSTOMER, address_mappings, DependencyResolver({}))
		row = self._base_row(
			billing_address_line1="123 Main St",
			billing_city="Delhi",
			billing_country="India",
			shipping_address_line1="123 Main St",
			shipping_city="Delhi",
			shipping_country="India",
		)
		party_name = creator.create(row)

		addresses = frappe.get_all(
			"Address",
			filters=[["Dynamic Link", "link_name", "=", party_name]],
			fields=["name", "is_primary_address", "is_shipping_address"],
		)
		self.assertEqual(len(addresses), 1, "Expected a single deduplicated address")
		addr = addresses[0]
		self.assertEqual(addr.is_primary_address, 1)
		self.assertEqual(addr.is_shipping_address, 1)

	def test_different_address_line1_creates_two_addresses(self):
		"""Different billing/shipping address_line1 → two separate Address records."""
		address_mappings = {
			"customer_name": "customer_name",
			"customer_group": "customer_group",
			"billing_address_line1": "billing_address_line1",
			"billing_city": "billing_city",
			"billing_country": "billing_country",
			"shipping_address_line1": "shipping_address_line1",
			"shipping_city": "shipping_city",
			"shipping_country": "shipping_country",
		}
		creator = PartyCreator(CUSTOMER, address_mappings, DependencyResolver({}))
		row = self._base_row(
			billing_address_line1="10 Office Park",
			billing_city="Delhi",
			billing_country="India",
			shipping_address_line1="45 Warehouse Rd",
			shipping_city="Mumbai",
			shipping_country="India",
		)
		party_name = creator.create(row)

		addresses = frappe.get_all(
			"Address",
			filters=[["Dynamic Link", "link_name", "=", party_name]],
			fields=["name", "is_primary_address", "is_shipping_address"],
		)
		self.assertEqual(len(addresses), 2, "Expected separate billing and shipping addresses")
		flags = {(a.is_primary_address, a.is_shipping_address) for a in addresses}
		self.assertIn((1, 0), flags)
		self.assertIn((0, 1), flags)


class TestContactDeduplication(UnitTestCase):
	TEST_EMAIL: ClassVar[str] = "pi_dedup_test@example.com"
	TEST_CUSTOMER_A: ClassVar[str] = "_PI Dedup Customer A"
	TEST_CUSTOMER_B: ClassVar[str] = "_PI Dedup Customer B"

	def tearDown(self):
		for customer_name in [self.TEST_CUSTOMER_A, self.TEST_CUSTOMER_B]:
			for name in frappe.get_all("Customer", filters={"customer_name": customer_name}, pluck="name"):
				frappe.delete_doc("Customer", name, ignore_permissions=True, force=True)
		for name in frappe.get_all(
			"Contact",
			filters=[["Contact Email", "email_id", "=", self.TEST_EMAIL]],
			pluck="name",
		):
			frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)

	def test_same_email_creates_one_contact_linked_to_both_parties(self):
		creator = PartyCreator(
			CUSTOMER,
			{
				"customer_name": "customer_name",
				"customer_group": "customer_group",
				"primary_email": "primary_email",
			},
			DependencyResolver({}),
		)
		creator.create(
			{
				"customer_name": self.TEST_CUSTOMER_A,
				"customer_group": "Commercial",
				"primary_email": self.TEST_EMAIL,
			}
		)
		creator.create(
			{
				"customer_name": self.TEST_CUSTOMER_B,
				"customer_group": "Commercial",
				"primary_email": self.TEST_EMAIL,
			}
		)

		contacts = frappe.get_all(
			"Contact", filters=[["Contact Email", "email_id", "=", self.TEST_EMAIL]], pluck="name"
		)
		self.assertEqual(len(contacts), 1, "Expected one deduplicated Contact")

		contact = frappe.get_doc("Contact", contacts[0])
		linked_names = {link.link_name for link in contact.links}
		customer_a = frappe.db.get_value("Customer", {"customer_name": self.TEST_CUSTOMER_A})
		customer_b = frappe.db.get_value("Customer", {"customer_name": self.TEST_CUSTOMER_B})
		self.assertIn(customer_a, linked_names)
		self.assertIn(customer_b, linked_names)


class TestMappingTemplates(UnitTestCase):
	"""save_mapping_template / list_mapping_templates / load_mapping_template / delete_mapping_template"""

	MAPPINGS: ClassVar[dict] = {"Customer Name": "customer_name", "Email": "primary_email"}

	def tearDown(self) -> None:
		frappe.db.delete("Party Import Mapping Template", {"owner": frappe.session.user})

	def test_save_creates_new_template(self):
		name = save_mapping_template("My Template", CUSTOMER, json.dumps(self.MAPPINGS))
		self.assertTrue(frappe.db.exists("Party Import Mapping Template", name))

	def test_save_overwrites_existing_template_with_same_name(self):
		updated = {"Customer Name": "customer_name", "Mobile": "primary_mobile"}
		save_mapping_template("Dup", CUSTOMER, json.dumps(self.MAPPINGS))
		name2 = save_mapping_template("Dup", CUSTOMER, json.dumps(updated))
		count = frappe.db.count(
			"Party Import Mapping Template",
			{"template_name": "Dup", "party_type": CUSTOMER, "owner": frappe.session.user},
		)
		self.assertEqual(count, 1)
		loaded = load_mapping_template(name2)
		self.assertEqual(loaded, updated)

	def test_list_returns_only_current_party_type(self):
		save_mapping_template("C Template", CUSTOMER, json.dumps(self.MAPPINGS))
		save_mapping_template("S Template", SUPPLIER, json.dumps({"Supplier Name": "supplier_name"}))
		results = list_mapping_templates(CUSTOMER)
		names = [r["template_name"] for r in results]
		self.assertIn("C Template", names)
		self.assertNotIn("S Template", names)

	def test_load_returns_mappings_dict(self):
		name = save_mapping_template("Load Me", CUSTOMER, json.dumps(self.MAPPINGS))
		loaded = load_mapping_template(name)
		self.assertEqual(loaded, self.MAPPINGS)

	def test_delete_removes_template(self):
		name = save_mapping_template("Delete Me", CUSTOMER, json.dumps(self.MAPPINGS))
		delete_mapping_template(name)
		self.assertFalse(frappe.db.exists("Party Import Mapping Template", name))

	def test_invalid_party_type_raises(self):
		with self.assertRaises(frappe.ValidationError):
			save_mapping_template("Bad", "Lead", json.dumps(self.MAPPINGS))
