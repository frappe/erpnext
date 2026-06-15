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
    if (message?.title === 'Message' || message?.title === 'Error') return "There was an error."
    return message?.title
}

const wrapLooseListItemsWithUl = (html: string): string => {
    // Regex matches consecutive <li>...</li> blocks not wrapped in <ul> or <ol>
    // It wraps them in a <ul> if not already wrapped.
    return html.replace(/(?:^|[^>])((<li[\s\S]*?<\/li>)+)(?![\s\S]*?<\/ul>)(?![\s\S]*?<\/ol>)/g, (match, p1) => {
        // Check if the match already has <ul> or <ol> wrapping (simple check)
        if (/^<ul>/.test(p1) || /^<ol>/.test(p1)) {
            return match // Already wrapped, keep as is
        }
        return match.replace(p1, `<ul>${p1}</ul>`)
    })
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
                    const safeMessage = wrapLooseListItemsWithUl(m.message)
                    return <MarkdownRenderer content={safeMessage} key={i} />
                })}
            </AlertDescription>
        </Alert>
    )
}

export default ErrorBanner