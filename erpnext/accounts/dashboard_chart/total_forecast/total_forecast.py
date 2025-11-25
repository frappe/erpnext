import frappe

@frappe.whitelist()
def get_overall_forecast_finance_chart_data():
    # Todo : Replace with actual data later
    receivables_due = frappe.db.sql("""
        SELECT IFNULL(SUM(outstanding_amount), 0)
        FROM `tabSales Invoice`
        WHERE status != 'Paid'
    """)[0][0]

    # Weekly GST Refunds Due
    gst_refunds_due = frappe.db.sql("""
    SELECT IFNULL(SUM(paid_amount), 0) AS gst_refunds_due
    FROM `tabPayment Entry`
    WHERE payment_type = 'Refund'
      AND status != 'Paid'
    """)[0][0] or 0

    # Overall Expenses for now only purchase invoice 
    # todo: Add other reports as well for expenses
    expenses_due = frappe.db.sql("""
        SELECT IFNULL(SUM(outstanding_amount), 0)
        FROM `tabPurchase Invoice`
        WHERE status != 'Paid'
    """)[0][0]

    income = receivables_due + gst_refunds_due
    expenses = expenses_due
    surplus_deficit = income - expenses
    return {
        "labels": ["Total"],  
        "datasets": [
            {"name": "Income", "values": [income], "color": "#74CF65"},
            {"name": "Expenses", "values": [expenses], "color": "#ED726A"},
            {"name": "Total Surplus/Deficit", "values": [surplus_deficit], "color": "#344EE4"}
        ],
        "type": "bar"
    }
