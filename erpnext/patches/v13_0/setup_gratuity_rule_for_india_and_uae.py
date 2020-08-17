# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import erpnext

def execute():
    region = erpnext.get_region()
    if region == "India":
        from erpnext.regional.india.setup import create_standard_documents
        create_standard_documents()
    elif region == "United Arab Emirates":
        from erpnext.regional.united_arab_emirates.setup import create_standard_documents
        create_standard_documents()