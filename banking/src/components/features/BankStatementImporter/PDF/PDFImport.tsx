import StatementDetails from '../CSV/StatementDetails'
import PDFTableEditor from './PDFTableEditor'
import { GetStatementDetailsResponse } from '../import_utils'

type Props = {
    data: { message: GetStatementDetailsResponse }
    mutate: () => void
}

const PDFImport = ({ data, mutate }: Props) => {
    return (
        <div className="w-full flex">
            <div className="w-[45%] p-4 h-[calc(100vh-72px)] overflow-scroll">
                <StatementDetails data={data.message} />
            </div>
            <div className="w-[55%] border-s pe-1 ps-0 border-outline-gray-2 h-[calc(100vh-72px)] overflow-scroll">
                <PDFTableEditor data={data.message} mutate={mutate} />
            </div>
        </div>
    )
}

export default PDFImport
