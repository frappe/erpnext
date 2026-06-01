import CSVRawDataPreview from './CSVRawDataPreview'
import StatementDetails from './StatementDetails'
import { GetStatementDetailsResponse } from '../import_utils'

const CSVImport = ({ data }: { data: { message: GetStatementDetailsResponse } }) => {



    return (
        <div className="w-full flex">
            <div className="w-[50%] p-4 h-[calc(100vh-72px)] overflow-scroll">
                <StatementDetails data={data.message} />
            </div>
            <div className="w-[50%] border-s border-t pe-1 ps-0 border-outline-gray-2 h-[calc(100vh-72px)] overflow-scroll">
                <CSVRawDataPreview data={data.message} />
            </div>
        </div>
    )
}

export default CSVImport