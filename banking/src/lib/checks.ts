/**
 * Function to check if a string exists in a list
 * @param list 
 * @param item 
 * @returns 
 */
export const in_list = (list: string[], item?: string): boolean => {
    if (item === undefined) return false

    return list.includes(item)
}

/**
 * Function to check if an object is empty
 * @param obj 
 * @returns 
 */
export const isEmpty = (obj: object) => {
    return Object.keys(obj).length === 0;
}