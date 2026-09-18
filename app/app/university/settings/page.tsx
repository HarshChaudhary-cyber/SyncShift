'use client';

import React, { useState, useEffect } from 'react';
import { useUniversity } from '../layout';
import { api, InstitutionUpdatePayload } from '@/lib/api';
import { showSuccessToast, showErrorToast } from '@/lib/toast';

export default function UniversitySettingsPage() {
  const { institution, isAdmin, refresh } = useUniversity();

  const [form, setForm] = useState<InstitutionUpdatePayload>({
    name: '',
    description: '',
    country: '',
    timezone: 'Europe/London',
    email_domain: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (institution) {
      setForm({
        name: institution.name || '',
        description: institution.description || '',
        country: institution.country || '',
        timezone: institution.timezone || 'Europe/London',
        email_domain: institution.email_domain || '',
      });
    }
  }, [institution]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !isAdmin) return;

    try {
      setSaving(true);
      await api.updateInstitution(institution.id, form);
      await refresh();
      showSuccessToast('Institution settings updated successfully!');
    } catch (err: unknown) {
      showErrorToast(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (!institution) {
    return (
      <div className="py-20 text-center text-xs text-[var(--text-secondary)]">
        No institution loaded.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚙️</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              University Settings
            </h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Manage institutional identity, campus timezone, email authentication domain, and policies.
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                Institution Name
              </label>
              <input
                type="text"
                required
                disabled={!isAdmin}
                value={form.name || ''}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-60"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                Institution Code
              </label>
              <input
                type="text"
                disabled
                value={institution.code}
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-muted)] cursor-not-allowed font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
              Description / Bio
            </label>
            <textarea
              rows={3}
              disabled={!isAdmin}
              value={form.description || ''}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-60"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                Country
              </label>
              <input
                type="text"
                disabled={!isAdmin}
                value={form.country || ''}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-60"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                Campus Timezone
              </label>
              <input
                type="text"
                disabled={!isAdmin}
                value={form.timezone || 'Europe/London'}
                onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-60"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                Allowed Email Domain
              </label>
              <input
                type="text"
                disabled={!isAdmin}
                placeholder="e.g. university.edu"
                value={form.email_domain || ''}
                onChange={(e) => setForm({ ...form, email_domain: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-60"
              />
            </div>
          </div>

          {isAdmin && (
            <div className="flex justify-end pt-4 border-t border-[var(--border-color)]">
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-md shadow-emerald-950/20 cursor-pointer"
              >
                {saving ? 'Saving changes…' : 'Save Institutional Settings'}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
