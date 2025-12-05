from datetime import datetime, timedelta, timezone
import frappe

FILTERS_KEY = "filters"
START_OFFSET_KEY = "start_offset"
END_OFFSET_KEY = "end_offset"

utc_now = datetime.now(timezone.utc)

invoice_filters = {
    "all": {
        START_OFFSET_KEY: None,
        END_OFFSET_KEY: None,
    },
    "undue": {
        START_OFFSET_KEY: None,
        END_OFFSET_KEY: 1,
    },
    "week": {
        START_OFFSET_KEY: ((utc_now + timedelta(days = 6 - utc_now.weekday())) - utc_now).days,
        END_OFFSET_KEY: ((utc_now + timedelta(days = -utc_now.weekday())) - utc_now).days,
    },
    "30": {
        START_OFFSET_KEY: 0,
        END_OFFSET_KEY: -30,
    },
    "60": {
        START_OFFSET_KEY: -31,
        END_OFFSET_KEY: -60,
    },
    "90": {
        START_OFFSET_KEY: -61,
        END_OFFSET_KEY: -90,
    },
    "120": {
        START_OFFSET_KEY: -91,
        END_OFFSET_KEY: -120,
    },
    "oldest": {
        START_OFFSET_KEY: -121,
        END_OFFSET_KEY: None,
    },
}


def get_today_as_string(offset: int):
  return (utc_now + timedelta(days=offset)).strftime("%Y-%m-%d")


def get_filter_condition(offset: int, operator: str):
  condition = ["due_date"]

  if offset is None:
    return None

  condition.append(operator)

  date = get_today_as_string(offset)
  condition.append(date)

  return condition


def construct_filter(filter_param: str):
  start_offset = invoice_filters[filter_param][START_OFFSET_KEY]
  end_offset = invoice_filters[filter_param][END_OFFSET_KEY]

  filter_conditions = [
      [
          "status",
          "!=",
          "Paid",
      ]
  ]

  gte_operator = ">="
  lte_operator = "<="

  start_conditions = get_filter_condition(
      start_offset,
      lte_operator,
  )

  if start_conditions is not None:
    filter_conditions.append(start_conditions)

  end_conditions = get_filter_condition(
      end_offset,
      gte_operator,
  )

  if end_conditions is not None:
    filter_conditions.append(end_conditions)

  return filter_conditions


@frappe.whitelist()
def get_invoices(filter_param: str, start: int, limit: int):
  try:
    # Use frappe.get_list to query the Purchase Invoice DocType
    invoices = frappe.get_list(
        "Purchase Invoice",
        fields=["*"],
        limit=100,
        order_by="due_date asc",
        filters=construct_filter(filter_param)  # invoice_filters[filter_param]
    )

    return invoices

  except KeyError:
    errmsg = "The given filter is not valid"
    frappe.errprint(errmsg)
    return {"error": errmsg}

  except Exception as e:
    frappe.log_error(frappe.get_traceback(), "Error fetching invoices")
    return {"error": str(e)}

@frappe.whitelist()
def process_multiple_payments(invoices):
    import json
    invoices = json.loads(invoices) if isinstance(invoices, str) else invoices

    for inv in invoices:
        inv_doc = frappe.get_doc("Purchase Invoice", inv)
        if inv_doc.outstanding_amount > 0:
            #  replace this with actual payment logic
            inv_doc.db_set("outstanding_amount", 0)
            frappe.db.commit()

    return "Payments processed successfully!"