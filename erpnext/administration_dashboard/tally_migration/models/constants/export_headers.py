from .import_types import *

headers = {
  JOURNAL_ENTRY_IMPORT: '"ID","Series","Entry Type","Company","Posting Date","Reference Number","Reference Date","User Remark","Multi Currency","Account (Accounting Entries)","Account Currency (Accounting Entries)","Credit (Accounting Entries)","Debit (Accounting Entries)","Exchange Rate (Accounting Entries)","Credit in Company Currency (Accounting Entries)","Debit in Company Currency (Accounting Entries)","Party (Accounting Entries)","Party Type (Accounting Entries)"',
  PAYMENT_ENTRY_IMPORT: '"ID","Series","Payment Type","Company","Posting Date","Cheque/Reference No","Cheque/Reference Date","Account Paid From","Account Currency (From)","Account Paid To","Account Currency (To)","Paid Amount","Source Exchange Rate","Received Amount","Target Exchange Rate","Party","Party Type"',
  PURCHASE_INVOICE_IMPORT: '"ID","Series","Reference No","Supplier","Date","Credit To","Purchase Taxes and Charges Template","Company","ID (Items)","Accepted Qty (Items)","Amount (Items)","Item Name (Items)","Rate (Items)","UOM (Items)","UOM Conversion Factor (Items)","Expense Head (Items)", "Item Tax Template (Items)", "Payment Terms Template"',
}

number_series = {
  JOURNAL_ENTRY_IMPORT: "ACC-JV-.YYYY.-",
  PAYMENT_ENTRY_IMPORT: "ACC-PAY-.YYYY.-",
  PURCHASE_INVOICE_IMPORT: "PINV-.YY.-",
}
