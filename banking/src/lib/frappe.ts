import { FrappeError } from "frappe-react-sdk"

interface ParsedErrorMessage {
    message: string,
    title?: string,
    indicator?: string,
}


export const getErrorMessage = (error?: FrappeError | null): string => {
    const messages = getErrorMessages(error)
    return messages.map(m => m.message).join('\n')
}

export const getErrorMessages = (error?: FrappeError | null): ParsedErrorMessage[] => {
    if (!error) return []
    let eMessages: ParsedErrorMessage[] = error?._server_messages ? JSON.parse(error?._server_messages) : []
    eMessages = eMessages.map((m) => {
        try {

            // @ts-expect-error - it can sometimes be a string
            return JSON.parse(m)

        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        catch (e) {
            return m
        }
    })

    if (eMessages.length === 0) {
        // Get the message from the exception by removing the exc_type
        const indexOfFirstColon = error?.exception?.indexOf(':')
        if (indexOfFirstColon) {
            const exception = error?.exception?.slice(indexOfFirstColon + 1)
            if (exception) {
                eMessages = [{
                    message: exception,
                    title: "Error"
                }]
            }
        }

        if (eMessages.length === 0) {
            eMessages = [{
                message: error?.message,
                title: "Error",
                indicator: "red"
            }]
        }
    }
    return eMessages

}

export const slug = (name?: string) => {
    return name?.toLowerCase().replace(/ /g, "-") ?? "";
}

export const getSystemDefault = (fieldName: string, fallback?: string) => {
    return window.frappe?.boot?.sysdefaults?.[fieldName] ?? fallback
}

export const getUserDefault = (fieldName: string, fallback?: string) => {
    return window.frappe?.boot?.user?.defaults?.[fieldName] ?? fallback
}

export const getBootFieldData = (fieldName: string, fallback?: string) => {
    return window.frappe?.boot?.[fieldName] ?? fallback
}