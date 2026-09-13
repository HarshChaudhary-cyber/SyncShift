'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import { api, InstitutionMembership } from '@/lib/api';

export default function UniversityMembersPage() {
  const { institution, isAdmin } = useUniversity();
  const [members, setMembers] = useState<InstitutionMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [role, setRole] = useState<'student' | 'professor' | 'admin'>('student');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadMembers = useCallback(async () => {
    if (!institution || !isAdmin) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getInstitutionMembers(institution.id);
      setMembers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load institution members');
    } finally {
      setLoading(false);
    }
  }, [institution, isAdmin]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (!institution || !isAdmin) return;
      try {
        setLoading(true);
        setError(null);
        const data = await api.getInstitutionMembers(institution.id);
        if (!cancelled) {
          setMembers(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load institution members');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [institution, isAdmin]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userEmail.trim()) {
      setFormError('User email is required.');
      return;
    }
    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);
      await api.addInstitutionMember(institution.id, {
        email: userEmail.trim().toLowerCase(),
        role,
      });
      setUserEmail('');
      setModalOpen(false);
      await loadMembers();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to add member. Ensure user exists and is not already enrolled.');
    } finally {
      setSubmitting(false);
    }
  };

  const getRoleBadge = (r: string) => {
    switch (r) {
      case 'admin':
      case 'super_admin':
        return 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30';
      case 'professor':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
      default:
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/30';
    }
  };

  if (!isAdmin) {
    return (
      <div className="text-center py-16 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)]">
        <span className="text-3xl block mb-2">🔒</span>
        <h3 className="text-base font-bold text-[var(--text-primary)]">Restricted Access</h3>
        <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
          Institution membership management is reserved for university administrators.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Students & Campus Members
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            View and manage enrolled students, faculty, and administrative members affiliated with {institution?.name || 'your university'}.
          </p>
        </div>

        <button
          onClick={() => {
            setUserEmail('');
            setRole('student');
            setFormError(null);
            setModalOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-sm cursor-pointer"
        >
          <span>+</span> Add Student or Member
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs text-[var(--text-secondary)]">Loading member directory…</p>
        </div>
      ) : (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--bg-elevated)] border-b border-[var(--border-color)] text-[var(--text-muted)] text-[11px] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Enrolled Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-primary)]">
                {members.map((m) => (
                  <tr key={m.id} className="hover:bg-[var(--bg-hover)]/40 transition">
                    <td className="py-3.5 px-4 font-semibold">
                      {m.user_name || 'SyncShift User'}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--text-secondary)] font-mono text-xs">
                      {m.user_email || `User #${m.user_id}`}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2.5 py-0.5 text-xs font-semibold rounded-full uppercase tracking-wider ${getRoleBadge(
                          m.role
                        )}`}
                      >
                        {m.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {m.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-[var(--text-muted)]">
                      {new Date(m.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal for Adding Member */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-[var(--text-primary)] mb-4">
              Add Institution Member
            </h3>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  User Email Address <span className="text-red-400">*</span>
                </label>
                <input
                  type="email"
                  required
                  placeholder="student@university.edu"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block">
                  The user must already have a registered SyncShift account.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Assigned Role <span className="text-red-400">*</span>
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as 'student' | 'professor' | 'admin')}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="student">Student (Standard academic access)</option>
                  <option value="professor">Professor (Faculty & course coordination)</option>
                  <option value="admin">Administrator (Full university management)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition disabled:opacity-50"
                >
                  {submitting ? 'Enrolling…' : 'Add Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
