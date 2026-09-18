'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import { api, AuditLogItem } from '@/lib/api';
import { showErrorToast } from '@/lib/toast';

export default function UniversityAuditLogsPage() {
  const { institution, isAdmin } = useUniversity();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getAuditLogs(100, 0);
      setLogs(res.items || []);
    } catch {
      showErrorToast('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📜</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Audit Logs</h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Immutable regulatory and security event trail for institution {institution?.name || ''}.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          className="px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-lg text-xs font-semibold transition cursor-pointer self-start sm:self-auto"
        >
          ↻ Refresh Logs
        </button>
      </div>

      {/* Security Status Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Recorded Actions</p>
          <p className="text-2xl font-black text-[var(--text-primary)] mt-1">{logs.length}</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Total logged events</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Access Control</p>
          <p className="text-sm font-semibold text-emerald-400 mt-2">Strict Tenant Isolation</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Admin-only visibility</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Integrity Verification</p>
          <p className="text-sm font-semibold text-indigo-400 mt-2">Tamper-Evident</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Append-only database journal</p>
        </div>
      </div>

      {/* Log Entries */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Security & Activity Stream</h2>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Loading audit journal…
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--text-muted)]">
            No audit records captured yet.
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-color)] font-mono text-xs">
            {logs.map((log) => (
              <div key={log.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold text-[10px]">
                      {log.action}
                    </span>
                    <span className="text-[var(--text-primary)] font-semibold font-sans">
                      {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''}
                    </span>
                  </div>
                  <p className="text-[var(--text-secondary)] text-[11px] font-sans">
                    {log.description || 'System state modification recorded'}
                  </p>
                </div>
                <div className="text-right text-[11px] text-[var(--text-muted)] shrink-0">
                  {new Date(log.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
