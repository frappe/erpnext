import { useGetStatementDetails } from '../import_utils'
import CSVRawDataPreview from './CSVRawDataPreview'
import StatementDetails from './StatementDetails'
import { SelectedBank } from '../../BankReconciliation/bankRecAtoms'
import ErrorBanner from '@/components/ui/error-banner'
import { Button } from '@/components/ui/button'
import { ChevronLeftIcon } from 'lucide-react'
import _ from '@/lib/translate'

const CSVImport = ({ bank, fileURL, onBack }: { bank: SelectedBank, fileURL: string, onBack: () => void }) => {

    const { data, error } = useGetStatementDetails(fileURL, bank.name)

    if (error) {
        return <div className='flex flex-col gap-4 px-4'>
            <div>
                <Button size='sm' variant='outline' onClick={onBack}>
                    <ChevronLeftIcon />
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
            <div className="w-[50%] border-l border-t pr-1 pl-0 border-border h-[calc(100vh-72px)] overflow-scroll">
                <CSVRawDataPreview data={data.message} />
            </div>
        </div>
    )
}

export default CSVImport