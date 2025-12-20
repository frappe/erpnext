from csv import DictReader
from io import StringIO


def extract(fileobj, *args, **kwargs):
	"""Extract incoterm titles from a CSV file."""
	file = StringIO(fileobj.read().decode())  # CSV reader expects a text file
	reader = DictReader(file)
	for i, row in enumerate(reader):
		yield i + 2, "_", row["title"], ["Title of an incoterm"]
