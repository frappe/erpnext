import re
import sys

errors_encounter = 0
pattern = re.compile(
	r"_\(([\"']{,3})(?P<message>((?!\1).)*)\1(\s*,\s*context\s*=\s*([\"'])(?P<py_context>((?!\5).)*)\5)*(\s*,(\s*?.*?\n*?)*(,\s*([\"'])(?P<js_context>((?!\11).)*)\11)*)*\)"
)
words_pattern = re.compile(r"_{1,2}\([\"'`]{1,3}.*?[a-zA-Z]")
start_pattern = re.compile(r"_{1,2}\([f\"'`]{1,3}")
f_string_pattern = re.compile(r"_\(f[\"']")
starts_with_f_pattern = re.compile(r"_\(f")

# skip first argument
files = sys.argv[1:]
files_to_scan = [_file for _file in files if _file.endswith((".py", ".js"))]

for _file in files_to_scan:
	with open(_file) as f:
		print(f"Checking: {_file}")
		file_lines = f.readlines()
		for line_number, line in enumerate(file_lines, 1):
			if "frappe-lint: disable-translate" in line:
				continue

			start_matches = start_pattern.search(line)
			if start_matches:
				starts_with_f = starts_with_f_pattern.search(line)

				if starts_with_f:
					has_f_string = f_string_pattern.search(line)
					if has_f_string:
						errors_encounter += 1
						print(
							f"\nF-strings are not supported for translations at line number {line_number}\n{line.strip()[:100]}"
						)
						continue
					else:
						continue

				match = pattern.search(line)
				error_found = False

				if not match and line.endswith((",\n", "[\n")):
					# concat remaining text to validate multiline pattern
					line = "".join(file_lines[line_number - 1 :])
					line = line[start_matches.start() + 1 :]
					match = pattern.match(line)

				if not match:
					error_found = True
					print(f"\nTranslation syntax error at line number {line_number}\n{line.strip()[:100]}")

				if not error_found and not words_pattern.search(line):
					error_found = True
					print(
						f"\nTranslation is useless because it has no words at line number {line_number}\n{line.strip()[:100]}"
					)

				if error_found:
					errors_encounter += 1

if errors_encounter > 0:
	print(
		'\nVisit "https://frappeframework.com/docs/user/en/translations" to learn about valid translation strings.'
	)
	sys.exit(1)
else:
	print("\nGood To Go!")
