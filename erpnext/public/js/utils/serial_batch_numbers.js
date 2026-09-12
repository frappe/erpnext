export function number_key(number) {
	return (number || "").trim().toUpperCase();
}

export function split_numbers(value) {
	return (value || "")
		.split(/[,\n]/)
		.map((number) => number.trim())
		.filter(Boolean);
}
