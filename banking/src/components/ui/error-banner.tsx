import { getErrorMessages } from '@/lib/frappe'
import { FrappeError } from 'frappe-react-sdk'
import { Alert, AlertDescription, AlertProps, AlertTitle } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import MarkdownRenderer from '@/components/ui/markdown'
import _ from '@/lib/translate'
import { useMemo } from 'react'

type ErrorBannerProps = AlertProps & {
    error?: FrappeError | null,
    overrideHeading?: string,
}

interface ParsedErrorMessage {
    message: string,
    title?: string,
    indicator?: string,
}

const parseHeading = (message?: ParsedErrorMessage) => {
    if (message?.title === 'Message' || message?.title === 'Error') return _("There was an error.")
    return message?.title
}

const ErrorBanner = ({ error, overrideHeading, ...props }: ErrorBannerProps) => {


    //exc_type: "ValidationError" or "PermissionError" etc
    // exc: With entire traceback - useful for reporting maybe
    // httpStatus and httpStatusText - not needed
    // _server_messages: Array of messages - useful for showing to user
    // console.log(JSON.parse(error?._server_messages!))

    const messages = useMemo(() => {
        return getErrorMessages(error)
    }, [error])

    return (
        <Alert theme={messages[0]?.indicator === 'yellow' ? 'amber' : "red"} {...props}>
            <AlertCircle />
            <AlertTitle>{overrideHeading ?? parseHeading(messages[0])}</AlertTitle>
            <AlertDescription>
                {messages.map((m, i) => {
                    return <MarkdownRenderer content={m.message} key={i} />
                })}
            </AlertDescription>
        </Alert>
    )
}

export default ErrorBanner