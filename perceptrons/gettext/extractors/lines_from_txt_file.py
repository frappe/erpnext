def extract(fileobj, *args, **kwargs):
	"""Split file into lines and yield one translation unit per line."""
	for line_no, line in enumerate(fileobj.readlines()):
		yield line_no + 1, "_", line.decode().strip(), []
