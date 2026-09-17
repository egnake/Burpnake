import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, Plus, X, Save, AlertCircle } from 'lucide-react';

export default function ScopeManager() {
  const [programName, setProgramName] = useState('');
  const [platform, setPlatform] = useState('hackerone');
  const [includeDomain, setIncludeDomain] = useState('');
  const [excludeDomain, setExcludeDomain] = useState('');
  const [includeDomains, setIncludeDomains] = useState([]);
  const [excludeDomains, setExcludeDomains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // Sayfa yüklendiğinde mevcut scope'u çek
  useEffect(() => {
    fetchCurrentScope();
  }, []);

  const fetchCurrentScope = async () => {
    try {
      const res = await axios.get('/api/scope/current');
      if (res.data.program_name) {
        setProgramName(res.data.program_name);
        setIncludeDomains(res.data.include_rules || []);
        setExcludeDomains(res.data.exclude_rules || []);
      }
    } catch (err) {
      console.error("Scope fetch error", err);
    }
  };

  const addDomain = (type) => {
    if (type === 'include' && includeDomain) {
      if (!includeDomains.includes(includeDomain)) setIncludeDomains([...includeDomains, includeDomain]);
      setIncludeDomain('');
    } else if (type === 'exclude' && excludeDomain) {
      if (!excludeDomains.includes(excludeDomain)) setExcludeDomains([...excludeDomains, excludeDomain]);
      setExcludeDomain('');
    }
  };

  const removeDomain = (type, domainToRemove) => {
    if (type === 'include') {
      setIncludeDomains(includeDomains.filter(d => d !== domainToRemove));
    } else {
      setExcludeDomains(excludeDomains.filter(d => d !== domainToRemove));
    }
  };

  const saveScope = async () => {
    if (!programName) {
      setMessage({ type: 'error', text: 'Program Name is required.' });
      return;
    }
    if (includeDomains.length === 0) {
      setMessage({ type: 'error', text: 'At least one In-Scope domain is required.' });
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      await axios.post('/api/scope/set', {
        program_name: programName,
        platform: platform,
        include_domains: includeDomains,
        exclude_domains: excludeDomains
      });
      setMessage({ type: 'success', text: 'Scope successfully saved and updated in backend.' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to save scope.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Shield className="w-8 h-8 text-primary-500" />
        <h1 className="text-3xl font-bold text-white">Target Scope Manager</h1>
      </div>

      {message && (
        <div className={`p-4 mb-6 rounded-lg flex items-center gap-3 ${message.type === 'success' ? 'bg-primary-500/10 border border-primary-500/50 text-primary-400' : 'bg-red-500/10 border border-red-500/50 text-red-400'}`}>
          <AlertCircle className="w-5 h-5" />
          <p>{message.text}</p>
        </div>
      )}

      <div className="bg-dark-800 p-6 rounded-xl border border-dark-700 shadow-xl mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Program Name</label>
            <input 
              type="text" 
              placeholder="e.g. Tesla Bug Bounty" 
              value={programName}
              onChange={(e) => setProgramName(e.target.value)}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-primary-500 transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Platform</label>
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-primary-500 transition-colors"
            >
              <option value="hackerone">HackerOne</option>
              <option value="bugcrowd">Bugcrowd</option>
              <option value="yeswehack">YesWeHack</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* In-Scope */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-primary-500"></span>
              In-Scope Domains
            </h3>
            <div className="flex gap-2 mb-4">
              <input 
                type="text" 
                placeholder="*.target.com"
                value={includeDomain}
                onChange={(e) => setIncludeDomain(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addDomain('include')}
                className="flex-1 bg-dark-900 border border-dark-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-primary-500"
              />
              <button onClick={() => addDomain('include')} className="bg-dark-700 hover:bg-dark-600 text-white px-3 py-2 rounded-lg transition-colors">
                <Plus className="w-5 h-5" />
              </button>
            </div>
            <ul className="space-y-2">
              {includeDomains.map((domain, i) => (
                <li key={i} className="flex items-center justify-between bg-dark-900 px-4 py-2 rounded-lg border border-dark-700/50">
                  <span className="text-slate-300 font-mono text-sm">{domain}</span>
                  <button onClick={() => removeDomain('include', domain)} className="text-slate-500 hover:text-red-400 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </li>
              ))}
              {includeDomains.length === 0 && <p className="text-sm text-slate-500 italic">No in-scope domains added.</p>}
            </ul>
          </div>

          {/* Out-of-Scope */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Out-of-Scope Domains
            </h3>
            <div className="flex gap-2 mb-4">
              <input 
                type="text" 
                placeholder="admin.target.com"
                value={excludeDomain}
                onChange={(e) => setExcludeDomain(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addDomain('exclude')}
                className="flex-1 bg-dark-900 border border-dark-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-red-500"
              />
              <button onClick={() => addDomain('exclude')} className="bg-dark-700 hover:bg-dark-600 text-white px-3 py-2 rounded-lg transition-colors">
                <Plus className="w-5 h-5" />
              </button>
            </div>
            <ul className="space-y-2">
              {excludeDomains.map((domain, i) => (
                <li key={i} className="flex items-center justify-between bg-dark-900 px-4 py-2 rounded-lg border border-dark-700/50">
                  <span className="text-slate-300 font-mono text-sm">{domain}</span>
                  <button onClick={() => removeDomain('exclude', domain)} className="text-slate-500 hover:text-red-400 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </li>
              ))}
              {excludeDomains.length === 0 && <p className="text-sm text-slate-500 italic">No out-of-scope domains added.</p>}
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-dark-700 flex justify-end">
          <button 
            onClick={saveScope}
            disabled={loading}
            className="bg-primary-600 hover:bg-primary-500 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <Save className="w-5 h-5" />
            {loading ? "Saving..." : "Save Scope Configuration"}
          </button>
        </div>
      </div>
      
      <div className="bg-dark-800/50 rounded-xl p-6 border border-dark-700">
        <h4 className="text-slate-200 font-medium mb-2">Wildcard Tips</h4>
        <p className="text-slate-400 text-sm">
          You can use asterisks (<code className="bg-dark-900 text-primary-400 px-1 rounded">*</code>) for wildcard matching. For example, 
          <code className="bg-dark-900 text-primary-400 px-1 rounded mx-1">*.example.com</code> will match <code>api.example.com</code> and <code>dev.api.example.com</code>.
          The AI will automatically filter incoming Burp requests based on these rules.
        </p>
      </div>
    </div>
  );
}
