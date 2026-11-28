const moment = () => window.moment;

const day = (value) => moment()(value).startOf("day");

export const days_until = (value) => day(value).diff(moment()().startOf("day"), "days");

export function short_date(value) {
	const date = moment()(value);
	return date.format(date.year() === moment()().year() ? "D MMM" : "D MMM YYYY");
}

export const long_date = (value) => moment()(value).format("D MMMM YYYY");
