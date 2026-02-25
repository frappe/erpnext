import { CheckCircle } from 'lucide-react'
import { Progress } from '../ui/progress'
import _ from '@/lib/translate'

const FileUploadBanner = ({
    uploadProgress,
}: { uploadProgress: number }) => {
    return <div className="flex items-center justify-center flex-col gap-4">
        <div className="flex flex-col items-center gap-4">
            <CheckCircle size={48} className="text-green-600" />
            <span className="text-accent-foreground">{_("The document has been created and reconciled. Uploading attachments...")}</span>
            <Progress value={Math.round(uploadProgress * 100)} />
        </div>
    </div>
}

export default FileUploadBanner