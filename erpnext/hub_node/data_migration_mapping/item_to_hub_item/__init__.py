import io, base64, urllib, os

def pre_process(doc):

	file_path = doc.image
	file_name = os.path.basename(file_path)

	if file_path.startswith('http'):
		url = file_path
		file_path = os.path.join('/tmp', file_name)
		urllib.urlretrieve(url, file_path)

	with io.open(file_path, 'rb') as f:
		doc.image = base64.b64encode(f.read())

	doc.image_file_name = file_name

	return doc

