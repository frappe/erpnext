import { useGetStatementDetails } from '../import_utils'
import CSVRawDataPreview from './CSVRawDataPreview'
import StatementDetails from './StatementDetails'
import { SelectedBank } from '../../BankReconciliation/bankRecAtoms'
import ErrorBanner from '@/components/ui/error-banner'
import { Button } from '@/components/ui/button'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import _ from '@/lib/translate'
import { useDirection } from '@/components/ui/direction'

const CSVImport = ({ bank, fileURL, onBack }: { bank: SelectedBank, fileURL: string, onBack: () => void }) => {

    const { data, error } = useGetStatementDetails(fileURL, bank.name)

    const direction = useDirection()

    if (error) {
        return <div className='flex flex-col gap-4 px-4'>
            <div>
                <Button size='sm' variant='outline' onClick={onBack}>
                    {direction === 'ltr' ? <ChevronLeftIcon /> : <ChevronRightIcon />}
                    {_("Back")}
                </Button>
            </div>
            <ErrorBanner error={error} />
        </div>
    }

    if (!data || !data.message) {
        return null
    }
    return (
        <div className="w-full flex">
            <div className="w-[50%] p-4 h-[calc(100vh-72px)] overflow-scroll">
                <StatementDetails data={data.message} bank={bank} onBack={onBack} />
            </div>
            <div className="w-[50%] border-s border-t pe-1 ps-0 border-outline-gray-2 h-[calc(100vh-72px)] overflow-scroll">
                <CSVRawDataPreview data={data.message} />
            </div>
        </div>
    )
}

export default CSVImport