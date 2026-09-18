'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import { api, InstitutionMembership } from '@/lib/api';
import { showErrorToast, showSuccessToast } from '@/lib/toast';

export default function UniversityStudentsPage() {
  const { institution, isAdmin } = useUniversity();
  const [students, setStudents] = useState<InstitutionMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadStudents = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const allMembers = await api.getInstitutionMembers(institution.id);
      const studentMembers = (allMembers || []).filter((m) => m.role === 'student');
      setStudents(studentMembers);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load students');
    } finally {
      setLoading(false);
    }
  }, [institution]);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !email.trim()) return;

    try {
      setSubmitting(true);
      await api.addInstitutionMember(institution.id, {
        email: email.trim(),
        role: 'student',
      });
      showSuccessToast(`Student ${email} enrolled in institution!`);
      setEmail('');
      setModalOpen(false);
      loadStudents();
    } catch (err) {
      showErrorToast(err instanceof Error ? err.message : 'Failed to add student');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">👥</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Student Roster</h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Directory of enrolled students at {institution?.name || 'the university'}.
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setModalOpen(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-950/20 self-start sm:self-auto"
          >
            + Enroll Student
          </button>
        )}
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Enrolled Students</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{students.length}</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Active student memberships</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Institution</p>
          <p className="text-base font-bold text-[var(--text-primary)] mt-1 truncate">
            {institution?.name || 'Not linked'}
          </p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{institution?.code || 'N/A'}</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Privacy Isolation</p>
          <p className="text-sm font-semibold text-emerald-400 mt-1">Protected</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
            Student work shifts & personal blocks are private
          </p>
        </div>
      </div>

      {/* Student List */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Enrolled Students List</h2>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Loading student directory…
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {error}
          </div>
        ) : students.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <span className="text-4xl">🎓</span>
            <p className="text-sm font-medium text-[var(--text-secondary)]">No students enrolled yet.</p>
            {isAdmin && (
              <button
                onClick={() => setModalOpen(true)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Enroll First Student
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-color)]">
            {students.map((student) => (
              <div key={student.id} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-400 font-bold text-xs shrink-0">
                    🎓
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      Student ID #{student.user_id}
                    </p>
                    <p className="text-xs text-[var(--text-secondary)] truncate">
                      Status: <span className="text-emerald-400 font-medium capitalize">{student.status}</span> · Joined{' '}
                      {new Date(student.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                  Student
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Enroll Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-[var(--text-primary)]">Enroll Student</h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleAddStudent} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                  Student Email
                </label>
                <input
                  type="email"
                  required
                  placeholder="student@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !email.trim()}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  {submitting ? 'Enrolling…' : 'Enroll Student'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
