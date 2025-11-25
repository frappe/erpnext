import frappe

@frappe.whitelist()
def get_weekly_forecast_finance_chart_data():
    # Todo : Replace with actual data later
    # Weekly Receivables Due
    receivables_due = frappe.db.sql("""
        SELECT IFNULL(SUM(outstanding_amount), 0)
        FROM `tabSales Invoice`
        WHERE status != 'Paid'
        AND due_date BETWEEN DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
        AND DATE_ADD(DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY), INTERVAL 6 DAY)
    """)[0][0]

    # Weekly GST Refunds Due
    gst_refunds_due = frappe.db.sql("""
    SELECT IFNULL(SUM(paid_amount), 0) AS gst_refunds_due
    FROM `tabPayment Entry`
    WHERE payment_type = 'Refund'
      AND status != 'Paid'
      AND posting_date BETWEEN CURDATE() - INTERVAL WEEKDAY(CURDATE()) DAY
                          AND CURDATE() + INTERVAL (6 - WEEKDAY(CURDATE())) DAY
    """)[0][0] or 0

    # Weekly Expenses for noe only purchase invoice 
    # todo: Add other reports as well for expenses
    expenses_due = frappe.db.sql("""
        SELECT IFNULL(SUM(outstanding_amount), 0)
        FROM `tabPurchase Invoice`
        WHERE status != 'Paid'
        AND due_date BETWEEN DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
        AND DATE_ADD(DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY), INTERVAL 6 DAY)
    """)[0][0]

    income = receivables_due + gst_refunds_due
    expenses = expenses_due
    surplus_deficit = income - expenses
    return {
        "labels": ["This Week"],  # only one label
        "datasets": [
            {"name": "Income", "values": [income], "color": "#3DB341"},
            {"name": "Expenses", "values": [expenses], "color": "#DA5248"},
            {"name": "Total Surplus/Deficit", "values": [surplus_deficit], "color": "#3093E4"}
        ],
        "type": "bar"
    }
