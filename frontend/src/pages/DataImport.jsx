import React, { useState } from 'react';
import { UploadCloud } from 'lucide-react';
import axios from 'axios';

export default function DataImport() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // API call to backend
      const res = await axios.post('/api/import/burp-xml', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(res.data);
    } catch (err) {
      alert("Error importing file");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-white mb-6">Data Import</h1>
      
      <div className="border-2 border-dashed border-dark-700 rounded-xl p-12 text-center hover:border-primary-500 transition-colors cursor-pointer bg-dark-800/50">
        <label className="cursor-pointer flex flex-col items-center">
          <UploadCloud className="w-16 h-16 text-slate-400 mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Upload Burp Suite XML</h3>
          <p className="text-slate-400 mb-6">Select a Burp Suite export file (XML base64 encoded format)</p>
          <input type="file" className="hidden" accept=".xml" onChange={handleFileUpload} />
          <span className="bg-primary-600 hover:bg-primary-500 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            {loading ? "Importing..." : "Select File"}
          </span>
        </label>
      </div>

      {result && (
        <div className="mt-8 p-6 bg-dark-800 rounded-xl border border-dark-700">
          <h3 className="text-xl font-bold text-white mb-2">Import Successful</h3>
          <p className="text-slate-300">Imported: <span className="text-primary-500 font-bold">{result.imported}</span> requests</p>
        </div>
      )}
    </div>
  );
}
