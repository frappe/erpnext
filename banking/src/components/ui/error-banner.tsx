import { getErrorMessage } from '@/lib/frappe'
import { FrappeError } from 'frappe-react-sdk'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import MarkdownRenderer from '@/components/ui/markdown'
import _ from '@/lib/translate'

type Props = {
    error: FrappeError | null,
    title?: string
}

const ErrorBanner = ({ error, title = _("There was an error.") }: Props) => {

    const errorMessage = getErrorMessage(error)
    return (
        <Alert variant='destructive'>
            <AlertCircle />
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription>
                <MarkdownRenderer content={errorMessage} />
            </AlertDescription>
        </Alert>
    )
}

export default ErrorBanner