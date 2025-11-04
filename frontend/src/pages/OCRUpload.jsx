import { useState } from 'react';
import { Upload, FileText, CheckCircle, Loader } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function OCRUpload() {
  const [uploading, setUploading] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);

  const handleFileUpload = async (e, type = 'invoice') => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setExtractedData(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      const endpoint = type === 'invoice' ? '/api/ocr/process-invoice' : '/api/ocr/process-receipt';
      
      const response = await axios.post(`${API_URL}${endpoint}`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setExtractedData(response.data);
    } catch (error) {
      console.error('Error processing document:', error);
      setError('Failed to process document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">OCR Document Processing</h1>
          <p className="text-gray-400">Upload invoices and receipts for automatic data extraction</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-8 border border-gray-700 hover:border-teal-500 transition-all">
            <div className="text-center">
              <FileText className="w-16 h-16 text-teal-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-white mb-2">Process Invoice</h2>
              <p className="text-sm text-gray-400 mb-6">
                Extract supplier details, amounts, line items, and tax information
              </p>
              <label className="inline-block px-6 py-3 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all cursor-pointer">
                <Upload className="w-5 h-5 inline mr-2" />
                Upload Invoice
                <input
                  type="file"
                  accept="image/*,.pdf"
                  onChange={(e) => handleFileUpload(e, 'invoice')}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-8 border border-gray-700 hover:border-purple-500 transition-all">
            <div className="text-center">
              <FileText className="w-16 h-16 text-purple-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-white mb-2">Process Receipt</h2>
              <p className="text-sm text-gray-400 mb-6">
                Extract merchant info, items, amounts, and payment details
              </p>
              <label className="inline-block px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all cursor-pointer">
                <Upload className="w-5 h-5 inline mr-2" />
                Upload Receipt
                <input
                  type="file"
                  accept="image/*,.pdf"
                  onChange={(e) => handleFileUpload(e, 'receipt')}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
            </div>
          </div>
        </div>

        {uploading && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-12 border border-gray-700 text-center">
            <Loader className="w-12 h-12 text-teal-400 animate-spin mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Processing Document...</h3>
            <p className="text-gray-400">Claude AI is analyzing your document</p>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 mb-6">
            <p className="text-red-400 font-medium">{error}</p>
          </div>
        )}

        {extractedData && !uploading && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <div className="flex items-center gap-3 mb-6">
              <CheckCircle className="w-8 h-8 text-green-400" />
              <div>
                <h2 className="text-2xl font-bold text-white">Extraction Complete!</h2>
                <p className="text-sm text-gray-400">Document: {extractedData.filename}</p>
              </div>
            </div>

            <div className="bg-gray-900/50 rounded-lg p-6 mb-4">
              <h3 className="text-lg font-semibold text-white mb-4">Extracted Data</h3>
              <pre className="text-sm text-gray-300 overflow-x-auto">
                {JSON.stringify(extractedData.extracted_data, null, 2)}
              </pre>
            </div>

            {extractedData.extracted_data && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {extractedData.extracted_data.supplier_name && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                    <p className="text-xs text-blue-300 mb-1">Supplier</p>
                    <p className="text-white font-semibold">{extractedData.extracted_data.supplier_name}</p>
                  </div>
                )}
                
                {extractedData.extracted_data.invoice_number && (
                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                    <p className="text-xs text-purple-300 mb-1">Invoice Number</p>
                    <p className="text-white font-semibold">{extractedData.extracted_data.invoice_number}</p>
                  </div>
                )}

                {extractedData.extracted_data.total_amount && (
                  <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                    <p className="text-xs text-green-300 mb-1">Total Amount</p>
                    <p className="text-white font-semibold">
                      {extractedData.extracted_data.currency} {extractedData.extracted_data.total_amount}
                    </p>
                  </div>
                )}

                {extractedData.extracted_data.invoice_date && (
                  <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4">
                    <p className="text-xs text-orange-300 mb-1">Date</p>
                    <p className="text-white font-semibold">{extractedData.extracted_data.invoice_date}</p>
                  </div>
                )}
              </div>
            )}

            <div className="mt-6 flex gap-4">
              <button className="flex-1 px-6 py-3 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all font-semibold">
                Create Invoice from Data
              </button>
              <button 
                onClick={() => setExtractedData(null)}
                className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-all"
              >
                Upload Another
              </button>
            </div>
          </div>
        )}

        <div className="mt-8 bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Supported Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-teal-400 mb-2">Invoice Extraction</h4>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Supplier name and details</li>
                <li>• Invoice number and date</li>
                <li>• Line items with quantities</li>
                <li>• Subtotal, tax, and total amounts</li>
                <li>• Tax ID (TPIN)</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-purple-400 mb-2">Receipt Extraction</h4>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Merchant name and location</li>
                <li>• Receipt number and timestamp</li>
                <li>• Purchased items list</li>
                <li>• Tax and total amounts</li>
                <li>• Payment method</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
