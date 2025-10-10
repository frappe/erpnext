function isLeapYear(year) {
    year = Number(year);
    if (!Number.isInteger(year)) {
        throw new Error('year must be an integer');
    }
    if (year % 4 !== 0) return false;
    if (year % 100 !== 0) return true;
    return year % 400 === 0;
}
function daysInYear(year) {
    return isLeapYear(year) ? 366 : 365;
}
console.log('2024 ->', isLeapYear(2024), daysInYear(2024));
console.log('2023 ->', isLeapYear(2023), daysInYear(2023));
console.log('2000 ->', isLeapYear(2000), daysInYear(2000));
console.log('1900 ->', isLeapYear(1900), daysInYear(1900));
