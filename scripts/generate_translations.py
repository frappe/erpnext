#!/usr/bin/env python3
"""
Generate Kurdish (ku) and complete Arabic (ar) translations for ZirakERP.
This script:
1. Creates a Kurdish PO file from the POT template with translations
2. Fills in missing Arabic translations
3. Covers all critical ERP/UI terms

Kurdish translations use Sorani (Central Kurdish) - ckb
Arabic translations use Modern Standard Arabic
"""

import re
import os
import sys

# ──────────────────────────────────────────────────────────────────────
# TRANSLATION DICTIONARIES
# ──────────────────────────────────────────────────────────────────────

# Core UI & Navigation
KURDISH_TRANSLATIONS = {
    # ── Login & Authentication ──
    "Login": "چوونەژوورەوە",
    "Logout": "چوونەدەرەوە",
    "Log in": "چوونەژوورەوە",
    "Log out": "چوونەدەرەوە",
    "Password": "وشەی نهێنی",
    "Forgot Password": "وشەی نهێنی لەبیرکردووە",
    "Forgot Password?": "وشەی نهێنی لەبیرکردووە؟",
    "Reset Password": "ڕێکخستنەوەی وشەی نهێنی",
    "Change Password": "گۆڕینی وشەی نهێنی",
    "Email": "ئیمەیڵ",
    "Email Address": "ناونیشانی ئیمەیڵ",
    "Username": "ناوی بەکارهێنەر",
    "Sign Up": "تۆمارکردن",
    "Sign In": "چوونەژوورەوە",
    "Remember me": "لەبیرم بهێڵەوە",
    "Welcome": "بەخێربێیت",

    # ── Common Actions ──
    "Save": "پاشەکەوتکردن",
    "Submit": "ناردن",
    "Cancel": "هەڵوەشاندنەوە",
    "Delete": "سڕینەوە",
    "Create": "دروستکردن",
    "Edit": "دەستکاریکردن",
    "New": "نوێ",
    "Print": "چاپکردن",
    "Search": "گەڕان",
    "Filter": "فلتەرکردن",
    "Add": "زیادکردن",
    "Remove": "لابردن",
    "Update": "نوێکردنەوە",
    "Close": "داخستن",
    "Open": "کردنەوە",
    "Back": "گەڕانەوە",
    "Next": "دواتر",
    "Previous": "پێشتر",
    "Refresh": "نوێکردنەوە",
    "Reload": "بارکردنەوە",
    "Import": "هاوردەکردن",
    "Export": "هەناردەکردن",
    "Download": "داگرتن",
    "Upload": "بارکردن",
    "Attach": "هاوپێچکردن",
    "Detach": "لاکردنەوە",
    "Copy": "لەبەرگرتنەوە",
    "Paste": "لکاندن",
    "Select": "هەڵبژاردن",
    "Select All": "هەڵبژاردنی هەموو",
    "Deselect All": "لابردنی هەڵبژاردن",
    "Apply": "جێبەجێکردن",
    "Clear": "پاککردنەوە",
    "Confirm": "دڵنیاکردنەوە",
    "OK": "باشە",
    "Yes": "بەڵێ",
    "No": "نەخێر",
    "Done": "تەواو",
    "Send": "ناردن",
    "Discard": "فڕێدان",
    "Continue": "بەردەوامبوون",
    "Retry": "هەوڵدانەوە",
    "Undo": "گەڕانەوە",
    "Redo": "دووبارەکردنەوە",
    "Duplicate": "دووبارەکردن",
    "Rename": "ناونانەوە",
    "Move": "گواستنەوە",
    "Merge": "تێکەڵکردن",
    "Split": "جیاکردنەوە",
    "View": "بینین",
    "Hide": "شاردنەوە",
    "Show": "نیشاندان",
    "Expand": "فراوانکردن",
    "Collapse": "کۆکردنەوە",

    # ── Navigation & Layout ──
    "Home": "سەرەتا",
    "Dashboard": "داشبۆرد",
    "Settings": "ڕێکخستنەکان",
    "Setup": "دامەزراندن",
    "Help": "یارمەتی",
    "About": "دەربارە",
    "Profile": "پڕۆفایل",
    "Notifications": "ئاگادارکردنەوەکان",
    "Messages": "نامەکان",
    "Menu": "مێنیو",
    "Sidebar": "لای لاپەڕە",
    "Toolbar": "تووڵامراز",
    "Workspace": "شوێنی کار",
    "Module": "مۆدیوول",
    "Report": "ڕاپۆرت",
    "Reports": "ڕاپۆرتەکان",
    "List": "لیست",
    "Form": "فۆرم",
    "Tree": "دار",
    "Calendar": "ڕۆژژمێر",
    "Gantt": "گانت",
    "Kanban": "کانبان",
    "Map": "نەخشە",
    "Image": "وێنە",
    "Inbox": "پۆستەی وەرگرتن",

    # ── Status & States ──
    "Status": "بارودۆخ",
    "Active": "چالاک",
    "Inactive": "ناچالاک",
    "Enable": "چالاککردن",
    "Disable": "ناچالاککردن",
    "Enabled": "چالاککراوە",
    "Disabled": "ناچالاککراوە",
    "Draft": "ڕەشنووس",
    "Pending": "چاوەڕوانە",
    "Approved": "پەسەندکراو",
    "Rejected": "ڕەتکراوەتەوە",
    "Submitted": "نێردراوە",
    "Cancelled": "هەڵوەشێنراوەتەوە",
    "Completed": "تەواوبووە",
    "Closed": "داخراوە",
    "Open": "کراوە",
    "Overdue": "دواکەوتووە",
    "On Hold": "ڕاگیراو",
    "In Progress": "لەڕێگادایە",
    "Not Started": "دەستپێنەکراوە",
    "Paid": "دراوە",
    "Unpaid": "نەدراوە",
    "Partially Paid": "بەشێکی دراوە",
    "Returned": "گەڕاوەتەوە",
    "Amended": "هەمواراکراوە",
    "Error": "هەڵە",
    "Success": "سەرکەوتوو",
    "Warning": "ئاگاداری",
    "Info": "زانیاری",

    # ── Time & Date ──
    "Date": "بەروار",
    "Time": "کات",
    "Today": "ئەمڕۆ",
    "Yesterday": "دوێنێ",
    "Tomorrow": "سبەینێ",
    "This Week": "ئەم هەفتەیە",
    "Last Week": "هەفتەی ڕابردوو",
    "This Month": "ئەم مانگە",
    "Last Month": "مانگی ڕابردوو",
    "This Year": "ئەم ساڵە",
    "Last Year": "ساڵی ڕابردوو",
    "From Date": "لە بەرواری",
    "To Date": "بۆ بەرواری",
    "Start Date": "بەرواری دەستپێکردن",
    "End Date": "بەرواری کۆتایی",
    "Due Date": "بەرواری دوایین",
    "Created": "دروستکراوە",
    "Modified": "گۆڕدراوە",
    "Posting Date": "بەرواری تۆمارکردن",
    "Transaction Date": "بەرواری مامەڵە",

    # ── Accounting & Finance ──
    "Account": "هەژمار",
    "Accounts": "هەژمارەکان",
    "Accounting": "ژمێریاری",
    "Invoice": "پسوولە",
    "Sales Invoice": "پسوولەی فرۆشتن",
    "Purchase Invoice": "پسوولەی کڕین",
    "Payment": "پارەدان",
    "Payment Entry": "تۆمارکردنی پارەدان",
    "Journal Entry": "تۆمارکردنی ڕۆژنامەوانی",
    "General Ledger": "دەفتەری گشتی",
    "Trial Balance": "هاوسەنگی تاقیکردنەوە",
    "Balance Sheet": "تەرازنامە",
    "Profit and Loss": "قازانج و زەرەر",
    "Income": "داهات",
    "Expense": "خەرجی",
    "Revenue": "داهات",
    "Cost": "تێچوو",
    "Tax": "باج",
    "Taxes": "باجەکان",
    "Discount": "داشکاندن",
    "Total": "کۆی گشتی",
    "Grand Total": "کۆی گشتی",
    "Net Total": "کۆی تەواو",
    "Amount": "بڕ",
    "Balance": "ماوە",
    "Debit": "قەرز",
    "Credit": "بستان",
    "Currency": "دراو",
    "Exchange Rate": "ڕێژەی ئاڵاوگۆڕ",
    "Fiscal Year": "ساڵی دارایی",
    "Cost Center": "ناوەندی تێچوو",
    "Budget": "بودجە",
    "Bank": "بانک",
    "Bank Account": "هەژماری بانکی",
    "Cash": "نەقد",
    "Cheque": "چەک",
    "Mode of Payment": "شێوازی پارەدان",
    "Chart of Accounts": "نەخشەی هەژمارەکان",
    "Accounts Receivable": "قەرزی وەرگیراو",
    "Accounts Payable": "قەرزی دراو",
    "Outstanding Amount": "بڕی ماوە",
    "Paid Amount": "بڕی دراو",
    "Write Off": "سڕینەوە",
    "Reconciliation": "ڕێکخستنەوە",
    "Period Closing Voucher": "بەڵگەنامەی داخستنی ماوە",
    "Financial Year": "ساڵی دارایی",

    # ── Buying & Selling ──
    "Buying": "کڕین",
    "Selling": "فرۆشتن",
    "Sales": "فرۆشتن",
    "Purchase": "کڕین",
    "Sales Order": "فەرمانی فرۆشتن",
    "Purchase Order": "فەرمانی کڕین",
    "Quotation": "نرخاندن",
    "Order": "فەرمان",
    "Supplier": "دابینکەر",
    "Suppliers": "دابینکەرەکان",
    "Customer": "کڕیار",
    "Customers": "کڕیارەکان",
    "Customer Group": "گروپی کڕیار",
    "Supplier Group": "گروپی دابینکەر",
    "Customer Name": "ناوی کڕیار",
    "Supplier Name": "ناوی دابینکەر",
    "Lead": "ئاڕاستەکراو",
    "Opportunity": "دەرفەت",
    "Delivery Note": "نووسراوی گەیاندن",
    "Purchase Receipt": "وەسڵی کڕین",
    "Return": "گەڕاندنەوە",
    "Pricing Rule": "یاسای نرخاندن",
    "Price List": "لیستی نرخ",
    "Buying Price List": "لیستی نرخی کڕین",
    "Selling Price List": "لیستی نرخی فرۆشتن",
    "Shopping Cart": "سەبەتەی کڕین",
    "Point of Sale": "خاڵی فرۆشتن",
    "POS": "خاڵی فرۆشتن",

    # ── Stock & Inventory ──
    "Stock": "کۆگا",
    "Inventory": "کۆگا",
    "Item": "بەرهەم",
    "Items": "بەرهەمەکان",
    "Item Code": "کۆدی بەرهەم",
    "Item Name": "ناوی بەرهەم",
    "Item Group": "گروپی بەرهەم",
    "Warehouse": "کۆگا",
    "Warehouses": "کۆگاکان",
    "Stock Entry": "تۆمارکردنی کۆگا",
    "Material Request": "داواکاری کەرەسە",
    "Material Transfer": "گواستنەوەی کەرەسە",
    "Stock Reconciliation": "ڕێکخستنەوەی کۆگا",
    "Batch": "کۆمەڵ",
    "Serial No": "ژمارەی زنجیرەیی",
    "Quantity": "بڕ",
    "Qty": "بڕ",
    "Rate": "نرخ",
    "UOM": "یەکەی پێوانە",
    "Unit of Measure": "یەکەی پێوانە",
    "Valuation Rate": "ڕێژەی نرخاندن",
    "Actual Qty": "بڕی ڕاستەقینە",
    "Projected Qty": "بڕی پێشبینیکراو",
    "Reserved Qty": "بڕی پارێزراو",
    "Ordered Qty": "بڕی فەرمانکراو",
    "Available Qty": "بڕی بەردەست",
    "In Stock": "لە کۆگا",
    "Out of Stock": "لە کۆگا نییە",
    "Reorder Level": "ئاستی فەرمانکردنەوە",
    "Safety Stock": "کۆگای ئاسایش",
    "Stock Balance": "ماوەی کۆگا",
    "Bin": "سندوق",

    # ── Manufacturing ──
    "Manufacturing": "بەرهەمهێنان",
    "BOM": "لیستی کەرەسە",
    "Bill of Materials": "لیستی کەرەسەکان",
    "Work Order": "فەرمانی کار",
    "Production Plan": "پلانی بەرهەمهێنان",
    "Workstation": "وێستگەی کار",
    "Operation": "کردار",
    "Raw Material": "کەرەسەی خام",
    "Finished Good": "بەرهەمی تەواو",
    "Scrap": "دەرچوو",

    # ── HR & Payroll ──
    "Human Resources": "سەرچاوەی مرۆیی",
    "HR": "سەرچاوەی مرۆیی",
    "Employee": "کارمەند",
    "Employees": "کارمەندەکان",
    "Employee Name": "ناوی کارمەند",
    "Department": "بەش",
    "Designation": "پلە",
    "Branch": "لق",
    "Salary": "مووچە",
    "Payroll": "لیستی مووچە",
    "Attendance": "ئامادەبوون",
    "Leave": "مۆڵەت",
    "Leave Application": "داواکاری مۆڵەت",
    "Leave Type": "جۆری مۆڵەت",
    "Holiday List": "لیستی پشوو",
    "Shift": "شیفت",
    "Overtime": "کاری زیادە",
    "Appraisal": "هەڵسەنگاندن",
    "Training": "ڕاهێنان",
    "Recruitment": "دامەزراندن",
    "Job Applicant": "داوای کار",

    # ── CRM ──
    "CRM": "بەڕێوەبردنی پەیوەندی کڕیاران",
    "Contact": "پەیوەندی",
    "Address": "ناونیشان",
    "Territory": "ناوچە",
    "Campaign": "کامپەین",
    "Sales Person": "فرۆشیار",
    "Sales Partner": "هاوبەشی فرۆشتن",
    "Communication": "پەیوەندی",

    # ── Projects ──
    "Projects": "پرۆژەکان",
    "Project": "پرۆژە",
    "Task": "ئەرک",
    "Tasks": "ئەرکەکان",
    "Milestone": "قۆناغ",
    "Timesheet": "کاتنامە",
    "Activity Type": "جۆری چالاکی",
    "Project Type": "جۆری پرۆژە",

    # ── Assets ──
    "Assets": "سامانەکان",
    "Asset": "سامان",
    "Asset Name": "ناوی سامان",
    "Asset Category": "پۆلی سامان",
    "Depreciation": "کەمبوونەوەی بەها",
    "Asset Maintenance": "چاککردنەوەی سامان",
    "Asset Movement": "جوڵەی سامان",

    # ── Support ──
    "Support": "پشتیوانی",
    "Issue": "کێشە",
    "Issues": "کێشەکان",
    "Warranty": "گەرەنتی",
    "Maintenance Visit": "سەردانی چاککردنەوە",
    "Maintenance Schedule": "خشتەی چاککردنەوە",

    # ── Quality ──
    "Quality Management": "بەڕێوەبردنی کوالیتی",
    "Quality Inspection": "پشکنینی کوالیتی",
    "Quality Procedure": "ڕێکاری کوالیتی",
    "Quality Goal": "ئامانجی کوالیتی",

    # ── Company & Setup ──
    "Company": "کۆمپانیا",
    "Companies": "کۆمپانیاکان",
    "Company Name": "ناوی کۆمپانیا",
    "User": "بەکارهێنەر",
    "Users": "بەکارهێنەرەکان",
    "Role": "ڕۆڵ",
    "Permission": "ڕێپێدان",
    "Permissions": "ڕێپێدانەکان",
    "Language": "زمان",
    "Country": "وڵات",
    "Region": "ناوچە",
    "City": "شار",
    "State": "پارێزگا",
    "Pincode": "کۆدی پۆستە",
    "Phone": "تەلەفۆن",
    "Mobile No": "ژمارەی مۆبایل",
    "Website": "ماڵپەڕ",
    "Logo": "لۆگۆ",
    "Default": "بنەڕەت",

    # ── Table & Data ──
    "Name": "ناو",
    "name": "ناو",
    "Description": "وەسف",
    "description": "وەسف",
    "Title": "سەردێڕ",
    "Type": "جۆر",
    "Category": "پۆل",
    "Group": "گروپ",
    "ID": "ناسنامە",
    "No.": "ژ.",
    "Sr": "ز",
    "Row": "ڕیز",
    "Column": "ستوون",
    "Table": "خشتە",
    "Total Rows": "کۆی ڕیزەکان",
    "Remarks": "تێبینی",
    "Note": "تێبینی",
    "Notes": "تێبینیەکان",
    "Comment": "لێدوان",
    "Comments": "لێدوانەکان",
    "Tag": "تاگ",
    "Tags": "تاگەکان",
    "Color": "ڕەنگ",
    "Owner": "خاوەن",
    "Amended From": "هەمواراکراوە لە",
    "Required": "پێویستە",
    "Optional": "ئارەزوومەندانە",
    "Mandatory": "ناچاری",
    "Read Only": "تەنها خوێندنەوە",
    "Hidden": "شاراوە",

    # ── Reports & Analytics ──
    "Profit": "قازانج",
    "Loss": "زەرەر",
    "Gross Profit": "قازانجی کۆ",
    "Net Profit": "قازانجی تەواو",
    "Margin": "مارجن",
    "Growth": "گەشە",
    "Trend": "ڕەوت",
    "Average": "تێکڕا",
    "Minimum": "کەمترین",
    "Maximum": "زۆرترین",
    "Count": "ژماردن",
    "Sum": "کۆ",
    "Percentage": "ڕێژە",
    "Ratio": "ڕێژە",
    "Chart": "هێڵکاری",
    "Graph": "گراف",

    # ── Miscellaneous ──
    "Yes": "بەڵێ",
    "No": "نەخێر",
    "All": "هەموو",
    "None": "هیچ",
    "Other": "تر",
    "Custom": "تایبەت",
    "Standard": "ستاندارد",
    "Advanced": "پێشکەوتوو",
    "Basic": "بنەڕەتی",
    "Details": "وردەکاریەکان",
    "Summary": "پوختە",
    "More": "زیاتر",
    "Less": "کەمتر",
    "Loading...": "باردەکرێت...",
    "Loading": "باردەکرێت",
    "Please wait...": "تکایە چاوەڕێبکە...",
    "Processing": "پرۆسەکردن",
    "Fetching...": "وەرگرتن...",
    "No results found": "هیچ ئەنجامێک نەدۆزرایەوە",
    "No data": "هیچ داتایەک نییە",
    "Not Permitted": "ڕێپێنەدراوە",
    "Not Found": "نەدۆزرایەوە",
    "Access Denied": "ڕێگەپێنەدراوە",
    "Are you sure?": "دڵنیایت؟",
    "Saved": "پاشەکەوتکرا",
    "Updated": "نوێکرایەوە",
    "Deleted": "سڕایەوە",
    "Created successfully": "بە سەرکەوتوویی دروستکرا",
    "Updated successfully": "بە سەرکەوتوویی نوێکرایەوە",
    "Deleted successfully": "بە سەرکەوتوویی سڕایەوە",
    "Row {0}": "ڕیز {0}",
    "Mandatory fields required in Row {0}": "خانەی ناچاری پێویستە لە ڕیز {0}",
    "and": "و",
    "or": "یان",
    "of": "ی",
    "for": "بۆ",
    "in": "لە",
    "is": "هەیە",
    "not": "نا",
    "with": "لەگەڵ",
    "from": "لە",
    "to": "بۆ",
    "by": "لەلایەن",

    # ── Print & PDF ──
    "Print Format": "شێوازی چاپ",
    "Letter Head": "سەرنامە",
    "Terms and Conditions": "مەرج و ڕێسا",
    "Print Heading": "سەردێڕی چاپ",
    "Header": "سەردێڕ",
    "Footer": "ژێرنووس",

    # ── Workflow ──
    "Workflow": "ڕێڕەوی کار",
    "Workflow State": "بارودۆخی ڕێڕەوی کار",
    "Workflow Action": "کرداری ڕێڕەوی کار",
    "Approve": "پەسەندکردن",
    "Reject": "ڕەتکردنەوە",
    "Review": "پێداچوونەوە",

    # ── Permissions & Security ──
    "Administrator": "بەڕێوەبەر",
    "System Manager": "بەڕێوەبەری سیستەم",
    "Guest": "میوان",
    "Allowed": "ڕێپێدراوە",
    "Not Allowed": "ڕێپێنەدراوە",
    "Restricted": "سنووردار",

    # ── Additional Setup Wizard ──
    "Select Language": "زمان هەڵبژێرە",
    "Select your language": "زمانی خۆت هەڵبژێرە",
    "Set Up Your Company": "کۆمپانیاکەت دابمەزرێنە",
    "What does your company do?": "کۆمپانیاکەت چی دەکات؟",
    "Company Abbreviation": "کورتکراوەی کۆمپانیا",
    "Financial Year": "ساڵی دارایی",
    "Bank Name": "ناوی بانک",
    "Chart of Accounts": "نەخشەی هەژمارەکان",
    "Complete Setup": "تەواوکردنی دامەزراندن",
    "Your setup is complete!": "دامەزراندنەکەت تەواو بوو!",
}

# Arabic translations for commonly missing strings
ARABIC_TRANSLATIONS = {
    # ── Login & Auth ──
    "Login": "تسجيل الدخول",
    "Logout": "تسجيل الخروج",
    "Password": "كلمة المرور",
    "Forgot Password": "نسيت كلمة المرور",
    "Forgot Password?": "نسيت كلمة المرور؟",
    "Reset Password": "إعادة تعيين كلمة المرور",
    "Change Password": "تغيير كلمة المرور",
    "Email Address": "عنوان البريد الإلكتروني",
    "Username": "اسم المستخدم",
    "Sign Up": "إنشاء حساب",
    "Sign In": "تسجيل الدخول",
    "Remember me": "تذكرني",
    "Welcome": "مرحباً",

    # ── Common Actions ──
    "Save": "حفظ",
    "Submit": "إرسال",
    "Cancel": "إلغاء",
    "Delete": "حذف",
    "Create": "إنشاء",
    "Edit": "تعديل",
    "New": "جديد",
    "Print": "طباعة",
    "Search": "بحث",
    "Filter": "تصفية",
    "Add": "إضافة",
    "Remove": "إزالة",
    "Update": "تحديث",
    "Close": "إغلاق",
    "Back": "رجوع",
    "Next": "التالي",
    "Previous": "السابق",
    "Refresh": "تحديث",
    "Import": "استيراد",
    "Export": "تصدير",
    "Download": "تنزيل",
    "Upload": "رفع",
    "Copy": "نسخ",
    "Select": "اختيار",
    "Select All": "اختيار الكل",
    "Apply": "تطبيق",
    "Clear": "مسح",
    "Confirm": "تأكيد",
    "OK": "موافق",
    "Yes": "نعم",
    "No": "لا",
    "Done": "تم",
    "Send": "إرسال",
    "Continue": "متابعة",
    "Duplicate": "نسخ مكرر",
    "Rename": "إعادة تسمية",
    "View": "عرض",
    "Hide": "إخفاء",
    "Show": "إظهار",
    "Expand": "توسيع",
    "Collapse": "طي",

    # ── Navigation ──
    "Home": "الرئيسية",
    "Dashboard": "لوحة القيادة",
    "Settings": "الإعدادات",
    "Setup": "الإعداد",
    "Help": "مساعدة",
    "About": "حول",
    "Profile": "الملف الشخصي",
    "Notifications": "الإشعارات",
    "Messages": "الرسائل",
    "Workspace": "مساحة العمل",
    "Module": "وحدة",
    "Report": "تقرير",
    "Reports": "التقارير",
    "List": "قائمة",
    "Calendar": "التقويم",

    # ── Status ──
    "Status": "الحالة",
    "Active": "نشط",
    "Inactive": "غير نشط",
    "Enable": "تمكين",
    "Disable": "تعطيل",
    "Enabled": "ممكّن",
    "Disabled": "معطّل",
    "Draft": "مسودة",
    "Pending": "قيد الانتظار",
    "Approved": "موافق عليه",
    "Rejected": "مرفوض",
    "Submitted": "مُقدَّم",
    "Cancelled": "ملغى",
    "Completed": "مكتمل",
    "Closed": "مغلق",
    "Overdue": "متأخر",
    "On Hold": "معلّق",
    "In Progress": "قيد التنفيذ",
    "Paid": "مدفوع",
    "Unpaid": "غير مدفوع",
    "Partially Paid": "مدفوع جزئياً",
    "Error": "خطأ",
    "Success": "نجاح",
    "Warning": "تحذير",

    # ── Date & Time ──
    "Date": "التاريخ",
    "Time": "الوقت",
    "Today": "اليوم",
    "Yesterday": "أمس",
    "Tomorrow": "غداً",
    "This Week": "هذا الأسبوع",
    "Last Week": "الأسبوع الماضي",
    "This Month": "هذا الشهر",
    "Last Month": "الشهر الماضي",
    "This Year": "هذا العام",
    "Last Year": "العام الماضي",
    "From Date": "من تاريخ",
    "To Date": "إلى تاريخ",
    "Start Date": "تاريخ البدء",
    "End Date": "تاريخ الانتهاء",
    "Due Date": "تاريخ الاستحقاق",
    "Posting Date": "تاريخ الترحيل",

    # ── Finance ──
    "Account": "حساب",
    "Accounts": "الحسابات",
    "Accounting": "المحاسبة",
    "Invoice": "فاتورة",
    "Sales Invoice": "فاتورة المبيعات",
    "Purchase Invoice": "فاتورة المشتريات",
    "Payment": "دفعة",
    "Payment Entry": "إدخال دفعة",
    "Journal Entry": "قيد يومية",
    "General Ledger": "دفتر الأستاذ العام",
    "Trial Balance": "ميزان المراجعة",
    "Balance Sheet": "الميزانية العمومية",
    "Profit and Loss": "الأرباح والخسائر",
    "Income": "الدخل",
    "Expense": "المصروف",
    "Revenue": "الإيرادات",
    "Cost": "التكلفة",
    "Tax": "ضريبة",
    "Taxes": "الضرائب",
    "Discount": "خصم",
    "Total": "المجموع",
    "Grand Total": "المجموع الكلي",
    "Net Total": "المجموع الصافي",
    "Amount": "المبلغ",
    "Balance": "الرصيد",
    "Debit": "مدين",
    "Credit": "دائن",
    "Currency": "العملة",
    "Exchange Rate": "سعر الصرف",
    "Fiscal Year": "السنة المالية",
    "Budget": "الميزانية",
    "Bank": "البنك",
    "Bank Account": "الحساب البنكي",
    "Cash": "نقدي",
    "Chart of Accounts": "شجرة الحسابات",
    "Accounts Receivable": "حسابات القبض",
    "Accounts Payable": "حسابات الدفع",

    # ── Buying & Selling ──
    "Buying": "المشتريات",
    "Selling": "المبيعات",
    "Sales": "المبيعات",
    "Purchase": "المشتريات",
    "Sales Order": "أمر البيع",
    "Purchase Order": "أمر الشراء",
    "Quotation": "عرض سعر",
    "Order": "أمر",
    "Supplier": "المورد",
    "Customer": "العميل",
    "Delivery Note": "إذن التسليم",
    "Purchase Receipt": "إيصال الشراء",
    "Price List": "قائمة الأسعار",
    "Point of Sale": "نقطة البيع",

    # ── Stock ──
    "Stock": "المخزون",
    "Inventory": "المخزون",
    "Item": "صنف",
    "Items": "الأصناف",
    "Item Code": "رمز الصنف",
    "Item Name": "اسم الصنف",
    "Item Group": "مجموعة الأصناف",
    "Warehouse": "المستودع",
    "Stock Entry": "إدخال مخزون",
    "Material Request": "طلب مواد",
    "Quantity": "الكمية",
    "Qty": "الكمية",
    "Rate": "السعر",
    "UOM": "وحدة القياس",
    "Unit of Measure": "وحدة القياس",

    # ── Manufacturing ──
    "Manufacturing": "التصنيع",
    "Bill of Materials": "قائمة المواد",
    "Work Order": "أمر العمل",
    "Production Plan": "خطة الإنتاج",
    "Raw Material": "مادة خام",
    "Finished Good": "منتج تام",

    # ── HR ──
    "Human Resources": "الموارد البشرية",
    "Employee": "موظف",
    "Department": "القسم",
    "Salary": "الراتب",
    "Payroll": "كشف الرواتب",
    "Attendance": "الحضور",
    "Leave": "إجازة",
    "Leave Application": "طلب إجازة",
    "Holiday List": "قائمة العطلات",

    # ── CRM ──
    "Contact": "جهة اتصال",
    "Address": "العنوان",
    "Territory": "المنطقة",
    "Campaign": "حملة",
    "Lead": "عميل محتمل",
    "Opportunity": "فرصة",

    # ── Projects ──
    "Project": "مشروع",
    "Task": "مهمة",
    "Milestone": "مرحلة",
    "Timesheet": "جدول زمني",

    # ── Assets ──
    "Asset": "أصل",
    "Assets": "الأصول",
    "Depreciation": "الإهلاك",

    # ── Support ──
    "Support": "الدعم",
    "Issue": "مشكلة",
    "Warranty": "الضمان",

    # ── Company & Setup ──
    "Company": "الشركة",
    "Company Name": "اسم الشركة",
    "User": "مستخدم",
    "Role": "دور",
    "Permission": "إذن",
    "Language": "اللغة",
    "Country": "البلد",
    "City": "المدينة",
    "Phone": "الهاتف",
    "Website": "الموقع الإلكتروني",

    # ── Data ──
    "Name": "الاسم",
    "Description": "الوصف",
    "Title": "العنوان",
    "Type": "النوع",
    "Category": "الفئة",
    "Group": "مجموعة",
    "Remarks": "ملاحظات",
    "Note": "ملاحظة",
    "Comment": "تعليق",
    "Required": "مطلوب",
    "Mandatory": "إلزامي",

    # ── Setup Wizard ──
    "Select Language": "اختر اللغة",
    "Select your language": "اختر لغتك",
    "Set Up Your Company": "إعداد شركتك",
    "Complete Setup": "إكمال الإعداد",
    "Administrator": "المدير",

    # ── Misc ──
    "Loading...": "جاري التحميل...",
    "Loading": "جاري التحميل",
    "Please wait...": "يرجى الانتظار...",
    "No results found": "لم يتم العثور على نتائج",
    "No data": "لا توجد بيانات",
    "Not Permitted": "غير مسموح",
    "Not Found": "غير موجود",
    "Access Denied": "تم رفض الوصول",
    "Are you sure?": "هل أنت متأكد؟",
    "Saved": "تم الحفظ",
    "All": "الكل",
    "None": "لا شيء",
    "Other": "أخرى",
    "Details": "التفاصيل",
    "Summary": "ملخص",
    "More": "المزيد",
    "Less": "أقل",
    "and": "و",
    "or": "أو",
    "of": "من",
    "for": "لـ",
    "in": "في",
    "from": "من",
    "to": "إلى",
    "by": "بواسطة",
}


def read_pot_file(pot_path):
    """Read the POT template and extract all msgid entries."""
    with open(pot_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content


def create_po_file(pot_path, output_path, lang_code, lang_name, translations, plural_forms):
    """Create a PO file from the POT template with translations."""
    with open(pot_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    i = 0
    in_header = True
    header_written = False

    while i < len(lines):
        line = lines[i]

        # Handle header
        if in_header and line.startswith('msgid ""') and i == 0:
            # Skip to msgstr and replace header
            output_lines.append('msgid ""\n')
            i += 1
            # Skip old msgstr
            output_lines.append('msgstr ""\n')
            i += 1
            # Write new header
            header = f'''"Project-Id-Version: ZirakERP\\n"
"Report-Msgid-Bugs-To: hello@frappe.io\\n"
"POT-Creation-Date: 2026-03-09 00:00+0000\\n"
"PO-Revision-Date: 2026-03-09 00:00+0000\\n"
"Last-Translator: ZirakERP Team\\n"
"Language-Team: {lang_name}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: ZirakERP Translation Script\\n"
{plural_forms}
"X-Crowdin-Language: {lang_code}\\n"
"Language: {lang_code}\\n"
'''
            output_lines.append(header)
            # Skip old header lines
            while i < len(lines) and lines[i].startswith('"'):
                i += 1
            in_header = False
            continue

        # Handle regular msgid/msgstr pairs
        if line.startswith("msgid "):
            in_header = False
            # Collect full msgid (may be multi-line)
            msgid_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith('"'):
                msgid_lines.append(lines[i])
                i += 1

            # Extract the msgid string
            msgid_text = ""
            for ml in msgid_lines:
                if ml.startswith("msgid "):
                    msgid_text += ml[7:-2]  # Remove 'msgid "' and '"\n'
                else:
                    msgid_text += ml[1:-2]  # Remove '"' and '"\n'

            # Write msgid lines as-is
            output_lines.extend(msgid_lines)

            # Now handle msgstr
            if i < len(lines) and lines[i].startswith("msgstr "):
                # Skip old msgstr (and any continuation lines)
                i += 1
                while i < len(lines) and lines[i].startswith('"'):
                    i += 1

            # Write our translation
            if msgid_text in translations:
                trans = translations[msgid_text]
                output_lines.append(f'msgstr "{trans}"\n')
            else:
                output_lines.append('msgstr ""\n')

            continue

        # Write all other lines as-is (comments, blank lines, etc.)
        output_lines.append(line)
        i += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    # Count translations
    translated = sum(1 for key in translations if key)
    print(f"  Created {output_path}")
    print(f"  Translations provided: {translated}")


def update_po_file(po_path, translations):
    """Update an existing PO file, filling in missing translations."""
    with open(po_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    i = 0
    filled_count = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("msgid "):
            # Collect full msgid
            msgid_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith('"') and not lines[i-1].startswith("msgstr"):
                msgid_lines.append(lines[i])
                i += 1

            # Extract msgid text
            msgid_text = ""
            for ml in msgid_lines:
                if ml.startswith("msgid "):
                    msgid_text += ml[7:-2]
                else:
                    msgid_text += ml[1:-2]

            output_lines.extend(msgid_lines)

            # Check msgstr
            if i < len(lines) and lines[i].startswith("msgstr "):
                msgstr_line = lines[i]
                msgstr_text = msgstr_line[8:-2]  # Extract value
                i += 1

                # Collect multi-line msgstr
                extra_msgstr = []
                while i < len(lines) and lines[i].startswith('"'):
                    msgstr_text += lines[i][1:-2]
                    extra_msgstr.append(lines[i])
                    i += 1

                # If empty and we have a translation, fill it in
                if msgstr_text == "" and msgid_text in translations:
                    output_lines.append(f'msgstr "{translations[msgid_text]}"\n')
                    filled_count += 1
                else:
                    output_lines.append(msgstr_line)
                    output_lines.extend(extra_msgstr)

                continue

        output_lines.append(line)
        i += 1

    with open(po_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"  Updated {po_path}")
    print(f"  Filled in {filled_count} missing translations")


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locale_dir = os.path.join(base_dir, "erpnext", "locale")
    pot_file = os.path.join(locale_dir, "main.pot")

    if not os.path.exists(pot_file):
        print(f"Error: POT file not found at {pot_file}")
        sys.exit(1)

    print("=" * 60)
    print("ZirakERP Translation Generator")
    print("=" * 60)

    # 1. Create Kurdish PO file
    print("\n[1/2] Creating Kurdish (Sorani) translation file...")
    ku_output = os.path.join(locale_dir, "ku.po")
    create_po_file(
        pot_file,
        ku_output,
        lang_code="ku",
        lang_name="Kurdish (Sorani)",
        translations=KURDISH_TRANSLATIONS,
        plural_forms='"Plural-Forms: nplurals=2; plural=(n != 1);\\n"'
    )

    # 2. Update Arabic PO file with missing translations
    print("\n[2/2] Completing Arabic translations...")
    ar_file = os.path.join(locale_dir, "ar.po")
    if os.path.exists(ar_file):
        update_po_file(ar_file, ARABIC_TRANSLATIONS)
    else:
        print(f"  Warning: Arabic PO file not found at {ar_file}")
        print("  Creating new Arabic PO file...")
        create_po_file(
            pot_file,
            ar_file,
            lang_code="ar",
            lang_name="Arabic",
            translations=ARABIC_TRANSLATIONS,
            plural_forms='"Plural-Forms: nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);\\n"'
        )

    print("\n" + "=" * 60)
    print("Translation files ready!")
    print(f"  Kurdish: {ku_output}")
    print(f"  Arabic:  {ar_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
