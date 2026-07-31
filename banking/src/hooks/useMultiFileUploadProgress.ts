import { useCallback, useRef, useState } from "react"

/** Tracks per-file upload progress (0–1) and exposes their average. */
export function useMultiFileUploadProgress() {
    const [uploadProgress, setUploadProgress] = useState(0)
    const fileProgressesRef = useRef<number[]>([])

    const startTracking = useCallback((fileCount: number) => {
        if (fileCount <= 0) {
            return
        }
        fileProgressesRef.current = new Array(fileCount).fill(0)
        setUploadProgress(0)
    }, [])

    const updateFileProgress = useCallback((fileIndex: number, progress: number) => {
        if (fileIndex < 0 || fileIndex >= fileProgressesRef.current.length) {
            return
        }

        if (fileProgressesRef.current.length === 0) {
            return
        }
        fileProgressesRef.current[fileIndex] = progress
        const total =
            fileProgressesRef.current.reduce((sum, p) => sum + p, 0) /
            fileProgressesRef.current.length
        setUploadProgress(total)
    }, [])

    const resetProgress = useCallback(() => {
        fileProgressesRef.current = []
        setUploadProgress(0)
    }, [])

    return { uploadProgress, startTracking, updateFileProgress, resetProgress }
}
