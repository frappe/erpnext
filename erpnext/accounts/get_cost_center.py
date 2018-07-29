# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe


@frappe.whitelist(allow_guest=True)
def get_cost_center():
    # 'account',
    try:
        data = frappe.form_dict

        account = data.get('account')
        frappe.set_user("Administrator")

    except Exception as e:
        return dict(status=False, message=str(e))
    return dict(status=True, message="")

