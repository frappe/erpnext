import time

import frappe

CHILD_TABLE = "tabSerial and Batch Entry"

CHUNK_SIZE = 50_000

# Denormalised columns copied from the bundle onto every entry row.
COLUMNS = (
	"posting_datetime",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"type_of_transaction",
	"is_cancelled",
	"item_code",
)


def execute():
	if not frappe.db.has_table("Serial and Batch Entry"):
		return

	# Only ever used to give the log a denominator. It is a cached information_schema
	# estimate, so it can read 0 for a table that has rows -- gating the backfill on it
	# would silently skip the whole migration. The loop below decides when it is done.
	total = frappe.db.estimate_count("Serial and Batch Entry")

	last_name = ""
	done = 0
	started_at = time.monotonic()

	while True:
		upper = get_chunk_end(last_name)

		update_chunk(last_name, upper)

		# Commit per chunk. Doing every row in one transaction grows the undo log until
		# each read has to walk it, which is what made this run for hours on large sites.
		frappe.db.commit()

		if not upper:
			# The tail is whatever was left after the last boundary, so it has to be
			# counted rather than assumed. Only ever scans a sub-chunk range.
			done += frappe.db.count("Serial and Batch Entry", {"name": (">", last_name)})
			log_progress(done, total, started_at)
			break

		# A bounded chunk is exactly CHUNK_SIZE rows by construction.
		done += CHUNK_SIZE
		last_name = upper
		log_progress(done, total, started_at)


def get_chunk_end(last_name):
	"""Return the name that closes the next chunk, or None when the tail is left.

	Keyset pagination, so each chunk is a sequential range scan on the clustered
	index rather than a deep OFFSET over the whole table.
	"""
	entry = frappe.qb.DocType("Serial and Batch Entry")

	boundary = (
		frappe.qb.from_(entry)
		.select(entry.name)
		.where(entry.name > last_name)
		.orderby(entry.name)
		.limit(1)
		.offset(CHUNK_SIZE - 1)
	).run(pluck=True)

	return boundary[0] if boundary else None


def update_chunk(last_name, upper):
	"""Copy the bundle's values onto one chunk of entries.

	Raw SQL because the query builder cannot express this statement. Every one of
	COLUMNS exists on both tables, and pypika renders the assignment target without
	its table (`_set_sql` forces `with_namespace=False`), so a joined UPDATE fails
	with "Column 'voucher_no' in field list is ambiguous". Aliasing the bundle in a
	derived table clears the ambiguity but makes MariaDB materialise the whole bundle
	table for every chunk and drive the join from it, and a correlated subquery per
	column costs one lookup per column per row instead of one per row.
	"""
	set_clause = ",\n\t\t\t\t".join(f"SABE.{column} = SABB.{column}" for column in COLUMNS)
	condition = "AND SABE.name <= %(upper)s" if upper else ""

	frappe.db.sql(
		f"""
			UPDATE `{CHILD_TABLE}` SABE
			INNER JOIN `tabSerial and Batch Bundle` SABB
				ON SABE.parent = SABB.name
			SET
				{set_clause}
			WHERE SABE.name > %(last_name)s {condition}
		""",
		{"last_name": last_name, "upper": upper},
	)


def log_progress(done, total, started_at):
	elapsed = time.monotonic() - started_at
	rate = done / elapsed if elapsed else 0
	print(
		f"Serial and Batch Entry: {done:,} rows of ~{total:,} ({rate:,.0f} rows/sec)",
		flush=True,
	)
