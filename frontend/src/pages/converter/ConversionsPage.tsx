/**
 * VELTO — My Conversions Page (History)
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRightLeft, Download, Search, Trash2 } from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import { Badge, EmptyState, SkeletonTable } from '../../components/ui/index';
import { conversionService } from '../../services/conversion';
import { formatFileSize, formatRelativeTime } from '../../utils';
import type { ConversionJob } from '../../types';

const FILTERS = [
  { label: 'All', value: '' },
  { label: 'Completed', value: 'completed' },
  { label: 'Processing', value: 'processing' },
  { label: 'Failed', value: 'failed' },
];

export default function ConversionsPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<ConversionJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (filter) params.status = filter;
      if (search.trim()) params.search = search.trim();
      const res = await conversionService.getHistory(params as any);
      setJobs(res.results);
      setTotalCount(res.count);
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, [filter, page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchJobs();
  };

  const handleDelete = async (jobId: string) => {
    try {
      await conversionService.deleteJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      setTotalCount((prev) => prev - 1);
    } catch {}
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <h1 className="text-2xl font-bold text-velto-ivory">My Conversions</h1>
          <Button variant="secondary" size="sm" onClick={() => navigate('/convert')} icon={<ArrowRightLeft className="h-4 w-4" />}>
            New Conversion
          </Button>
        </div>

        {/* Filters + Search */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="flex gap-1 overflow-x-auto pb-1">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => { setFilter(f.value); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  filter === f.value
                    ? 'bg-velto-gold/10 text-velto-gold border border-velto-gold/20'
                    : 'text-velto-muted hover:text-velto-ivory hover:bg-velto-surface-3 border border-transparent'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <form onSubmit={handleSearch} className="flex-1 max-w-xs">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-velto-dim" />
              <input
                type="search"
                placeholder="Search files..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-velto-surface-2 border border-velto-surface-4 rounded-lg pl-9 pr-4 py-2 text-sm text-velto-ivory placeholder:text-velto-dim focus:border-velto-gold/50 focus:ring-1 focus:ring-velto-gold/15"
              />
            </div>
          </form>
        </div>

        {/* Content */}
        {loading ? (
          <SkeletonTable rows={5} />
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={<ArrowRightLeft className="h-12 w-12" />}
            title="No conversions yet"
            description="Your completed conversions will appear here."
            action={<Button variant="primary" onClick={() => navigate('/convert')}>Start Converting</Button>}
          />
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden md:block bg-velto-surface border border-velto-surface-4 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-velto-surface-4">
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">File</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">From</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">To</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">Status</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">Size</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">Date</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-velto-dim uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-velto-surface-4">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-velto-surface-2/50 transition-colors">
                      <td className="px-4 py-3 text-sm text-velto-ivory max-w-[200px] truncate">{job.original_filename}</td>
                      <td className="px-4 py-3 text-sm text-velto-muted">{job.source_format.toUpperCase()}</td>
                      <td className="px-4 py-3 text-sm text-velto-muted">{job.target_format.toUpperCase()}</td>
                      <td className="px-4 py-3"><Badge status={job.status} /></td>
                      <td className="px-4 py-3 text-sm text-velto-muted">{formatFileSize(job.file_size_bytes)}</td>
                      <td className="px-4 py-3 text-sm text-velto-dim">{formatRelativeTime(job.created_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {job.download_available && (
                            <button onClick={() => conversionService.downloadFile(job.id)} className="p-1.5 rounded-md text-velto-dim hover:text-velto-gold hover:bg-velto-gold/10 transition-colors" aria-label="Download">
                              <Download className="h-4 w-4" />
                            </button>
                          )}
                          <button onClick={() => handleDelete(job.id)} className="p-1.5 rounded-md text-velto-dim hover:text-red-400 hover:bg-red-500/10 transition-colors" aria-label="Delete">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="bg-velto-surface border border-velto-surface-4 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p className="text-sm text-velto-ivory font-medium truncate flex-1">{job.original_filename}</p>
                    <Badge status={job.status} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-velto-dim mb-3">
                    <span>{job.source_format.toUpperCase()} → {job.target_format.toUpperCase()}</span>
                    <span>·</span>
                    <span>{formatFileSize(job.file_size_bytes)}</span>
                    <span>·</span>
                    <span>{formatRelativeTime(job.created_at)}</span>
                  </div>
                  <div className="flex gap-2">
                    {job.download_available && (
                      <Button variant="secondary" size="sm" icon={<Download className="h-3.5 w-3.5" />} onClick={() => conversionService.downloadFile(job.id)}>Download</Button>
                    )}
                    <Button variant="ghost" size="sm" icon={<Trash2 className="h-3.5 w-3.5" />} onClick={() => handleDelete(job.id)}>Delete</Button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
                <span className="text-sm text-velto-muted">Page {page} of {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
