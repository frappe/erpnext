import frappe
import os
import tempfile
import zipfile
import csv
import re
from pathlib import Path
from erpnext.administration_dashboard.tally_migration.services.entries_service import get_entries
from erpnext.administration_dashboard.tally_migration.services.export_service import get_csv_entries, save_as_file, archive_files
from erpnext.administration_dashboard.tally_migration.services.accounts_service import (
    load_accounts_from_csv,
    load_accounts_dict_from_csv,
    load_items_from_csv,
    load_items_dict_from_csv,
    load_all_parties_from_csv,
)
from frappe.model.document import Document

class DataConversion(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        accounts_dictionary: DF.Attach | None
        amended_from: DF.Link | None
        company: DF.Link
        file: DF.Attach
        missing_accounts: DF.LongText | None
        missing_items: DF.LongText | None
        processed_zip_file: DF.LongText | None
    # end: auto-generated types

    def prepare_source_files(self):
        file_doc = frappe.get_doc("File", {"file_url": self.file})
        uploaded_path = frappe.get_site_path(file_doc.file_url.lstrip("/"))
        
        if uploaded_path.lower().endswith((".xls", ".xlsx")):
            return [uploaded_path]
        
        elif uploaded_path.lower().endswith(".zip"):
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(uploaded_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
            source_excels = [
                str(p)
                for p in Path(temp_dir).rglob("*.xls*")
                if not p.name.startswith("~")  # skip temp Excel files
            ]
            if not source_excels:
                frappe.throw("No Excel files found in the uploaded ZIP.")
            return source_excels

        else:
            frappe.throw(
                "Unsupported file type. Please upload an Excel (.xls/.xlsx) "
                "or ZIP file containing Excel files."
            )
    
    def load_masters(self):
        accounts = frappe.get_all(
            "Account",
            filters={"company": self.company},
            fields=["name", "account_name", "parent_account", "is_group", "account_type", "disabled"]
        )

        erpnext_acc_map = {acc["account_name"]: acc for acc in accounts}
        accounts_dict = {}

         # Use uploaded accounts dictionary CSV, if present
        if self.accounts_dictionary:
            file_doc = frappe.get_doc("File", {"file_url": self.accounts_dictionary})
            file_path = frappe.get_site_path(file_doc.file_url.lstrip("/"))

            # Use the existing helper to load dictionary mapping from CSV file
            alias_mapping = load_accounts_dict_from_csv(file_path)

            # Map aliases to ERPNext accounts
            for alias, mapped_acc_name in alias_mapping.items():
                erpnext_acc = erpnext_acc_map.get(mapped_acc_name)
                if erpnext_acc:
                    accounts_dict[alias] = erpnext_acc
                else:
                    # Optional: handle unmapped or missing accounts gracefully
                    accounts_dict[alias] = None

        # Add all direct ERPNext accounts to accounts_dict (aliases matching actual account names)
        for acc_name, acc in erpnext_acc_map.items():
            if acc_name not in accounts_dict:
                accounts_dict[acc_name] = acc

        items_list = frappe.get_all(
            "Item",
            fields=["name", "item_code", "item_name", "item_group", "is_stock_item", "disabled"]
        )
        
        items_dict = {item["item_code"]: item for item in items_list}

        suppliers = frappe.get_all(
            "Supplier",
            fields=["name", "supplier_name"]
        )

        # Get all customers
        customers = frappe.get_all(
            "Customer",
            fields=["name", "customer_name"]
        )
        company_abbr = frappe.db.get_value("Company", self.company, "abbr") or self.company.upper()
        app_path = Path(frappe.get_app_path("erpnext"))
        parties = []
        parties.extend(suppliers)
        parties.extend(customers)

        return accounts, accounts_dict, parties, items_list, items_dict

    @frappe.whitelist()
    def process_upload(self):
        source_excels = self.prepare_source_files()
        company_abbr = frappe.db.get_value("Company", self.company, "abbr") or self.company.upper()

        accounts, accounts_dict, parties, items_list, items_dict = self.load_masters()

        invalid_accounts = []
        invalid_items = []
        extracts = []

        for source_excel in source_excels:
            print(f"Processing file: {source_excel}")
            print(f"Loaded accounts: {len(accounts)}, items: {len(items_list)}, parties: {len(parties)}")
            extract = get_entries(
                source_excel,
                accounts,
                accounts_dict,
                parties,
                items_list,
                items_dict,
                self.company,
                company_abbr,
            )

            print(f"Entries found: {len(extract.entries) if extract.entries else 0}")
            print(f"Invalid accounts: {extract.invalid_accounts}")

            if extract.invalid_accounts:
                invalid_accounts.extend(
                    x for x in extract.invalid_accounts if x not in invalid_accounts
                )
            if getattr(extract, "invalid_items", []):
                invalid_items.extend(
                    x for x in extract.invalid_items if x not in invalid_items
                )
            extracts.append(extract)

        # Save missing data state in DocType
        if invalid_accounts or invalid_items:
            self.db_set("missing_accounts", ",".join(invalid_accounts))
            self.db_set("missing_items", ",".join(invalid_items))
            self.db_set("processed_zip_file", "")

            print(f"Missing accounts saved: {self.missing_accounts}")
            print(f"Missing items saved: {self.missing_items}")
            return {
                "missing_accounts": ",".join(invalid_accounts),
                "missing_items": ",".join(invalid_items),
            }
        else:
            self.db_set("missing_accounts", "")
            self.db_set("missing_items", "")

        output_folder = frappe.get_site_path("private", "files", f"{self.name}_exports")
        os.makedirs(output_folder, exist_ok=True)

        all_csv_files = []
        for extract in extracts:
            je, pe, pi = get_csv_entries(extract.entries, accounts)
            all_csv_files.append(save_as_file(je, f"journal_entries_{extract.source_filename}", output_folder))
            all_csv_files.append(save_as_file(pe, f"payment_entries_{extract.source_filename}", output_folder))
            all_csv_files.append(save_as_file(pi, f"purchase_invoices_{extract.source_filename}", output_folder))

        input_file_doc = frappe.get_doc("File", {"file_url": self.file})
        input_file_name = os.path.basename(input_file_doc.file_url)
        base_name = os.path.splitext(input_file_name)[0]
        sanitized_base_name = re.sub(r'[^\w\- ]', '', base_name)
        # sanitized_base_name = sanitized_base_name.replace(" ", "_")
        sanitized_base_name = re.sub(r'\s+', '_', sanitized_base_name)

        exported_zip_suffix = f"{sanitized_base_name}"
        zip_path = archive_files(all_csv_files, filename_suffix=exported_zip_suffix, output_folder=output_folder)

        with open(zip_path, "rb") as f:
            filedata = f.read()

        saved_file = frappe.utils.file_manager.save_file(
            os.path.basename(zip_path), filedata, "Data Conversion", self.name, is_private=1
        )

        self.db_set("processed_zip_file", saved_file.file_url)
        return saved_file.file_url
    
    def autoname(self):
        if not self.file:
            self.name = self.get_default_name()
            return
        file_doc = frappe.get_doc("File", {"file_url": self.file})

        # Extract base filename without extension
        file_name = os.path.basename(file_doc.file_url)
        base_name = os.path.splitext(file_name)[0]
        sanitized_name = re.sub(r'[^\w\s\-]', '', base_name).strip()
        new_name = sanitized_name
        suffix = 1

        while frappe.db.exists(self.doctype, new_name):
            new_name = f"{sanitized_name}_{suffix}"
            suffix += 1

        self.name = new_name
        
@frappe.whitelist()
def process_upload(docname):
    doc = frappe.get_doc("Data Conversion", docname)
    return doc.process_upload()
