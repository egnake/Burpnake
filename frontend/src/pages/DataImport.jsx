import React, { useState } from 'react';
import { UploadCloud, AlertCircle, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

export default function DataImport() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);

    const isHar = file.name.toLowerCase().endsWith('.har');
    const endpoint = isHar ? '/api/import/har' : '/api/import/burp-xml';

    try {
      const res = await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error importing file. Verify XML/HAR format.');
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-white mb-6">Data Import</h1>

      {error && (
        <div className="mb-6 p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      <div className="border-2 border-dashed border-dark-700 rounded-xl p-12 text-center hover:border-primary-500 transition-colors cursor-pointer bg-dark-800/50">
        <label className="cursor-pointer flex flex-col items-center">
          <UploadCloud className="w-16 h-16 text-slate-400 mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Upload Burp Suite XML or HAR</h3>
          <p className="text-slate-400 mb-6">Select a Burp Suite XML export (.xml) or HTTP Archive (.har) file</p>
          <input type="file" className="hidden" accept=".xml,.har" onChange={handleFileUpload} />
          <span className="bg-primary-600 hover:bg-primary-500 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            {loading ? 'Importing...' : 'Select File'}
          </span>
        </label>
      </div>

      {result && (
        <div className="mt-8 p-6 bg-dark-800 rounded-xl border border-dark-700">
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-400" /> Import Successful
          </h3>
          <p className="text-slate-300">
            Imported: <span className="text-primary-500 font-bold">{result.imported}</span> in-scope requests
            {result.summary?.unique_hosts?.length > 0 && (
              <span className="text-slate-400 text-sm ml-2">
                ({result.summary.unique_hosts.length} host)
              </span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
