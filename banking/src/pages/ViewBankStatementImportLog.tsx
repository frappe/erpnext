import { lazy } from 'react'
import { useGetStatementDetails } from '@/components/features/BankStatementImporter/import_utils'
import { Button } from '@/components/ui/button'
import { useDirection } from '@/components/ui/direction'
import ErrorBanner from '@/components/ui/error-banner'
import _ from '@/lib/translate'
import { useFrappeDocumentEventListener } from 'frappe-react-sdk'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import { Link, useParams } from 'react-router'

const CSVImport = lazy(() => import('@/components/features/BankStatementImporter/CSV/CSVImport'))
const PDFImport = lazy(() => import('@/components/features/BankStatementImporter/PDF/PDFImport'))

const ViewBankStatementImportLog = () => {

    const { id } = useParams<{ id: string }>()

    const { data, isLoading, error, mutate } = useGetStatementDetails(id ?? "")

    useFrappeDocumentEventListener("Bank Statement Import Log", id ?? "", () => {
    })

    const direction = useDirection()

    if (!data || !data.message) {
        return null
    }

    if (isLoading) {
        return <div>Loading...</div>
    }

    if (error) {
        return <div className='flex flex-col gap-4 px-4'>
            <div>
                <Button size='sm' variant='outline' asChild>
                    <Link to="/statement-importer">
                        {direction === 'ltr' ? <ChevronLeftIcon /> : <ChevronRightIcon />}
                        {_("Back")}
                    </Link>
                </Button>
            </div>
            <ErrorBanner error={error} />
        </div>
    }
    const isPdf = data.message.doc.file?.toLowerCase().endsWith('.pdf')

    if (isPdf) {
        return <PDFImport data={data} mutate={mutate} />
    }

    return <CSVImport data={data} mutate={mutate} />
}

export default ViewBankStatementImportLog