'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import CustomSelect from '@/components/ui/CustomSelect';
import {
  api,
  FacultyProfile,
  FacultyProfileCreatePayload,
  FacultyProfileUpdatePayload,
  Department,
  InstitutionMembership,
} from '@/lib/api';

export default function FacultyPage() {
  const { institution, isAdmin } = useUniversity();
  const [facultyList, setFacultyList] = useState<FacultyProfile[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [members, setMembers] = useState<InstitutionMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingFaculty, setEditingFaculty] = useState<FacultyProfile | null>(null);
  const [addMode, setAddMode] = useState<'member' | 'email'>('member');
  const [selectedUserId, setSelectedUserId] = useState<number>(0);
  const [userEmailInput, setUserEmailInput] = useState<string>('');
  const [formDeptId, setFormDeptId] = useState<number | undefined>(undefined);
  const [formTitle, setFormTitle] = useState<string>('Professor');
  const [formEmployeeCode, setFormEmployeeCode] = useState<string>('');
  const [formStatus, setFormStatus] = useState<string>('active');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const [facData, deptsData] = await Promise.all([
        api.getFaculty(institution.id, {
          department_id: deptFilter !== 'all' ? Number(deptFilter) : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          search: search.trim() || undefined,
        }),
        api.getDepartments(institution.id),
      ]);
      setFacultyList(facData);
      setDepartments(deptsData);

      // Load members for creation picker if admin
      if (isAdmin) {
        try {
          const membersData = await api.getInstitutionMembers(institution.id);
          setMembers(membersData);
        } catch {
          // Non-blocking if members list fails
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load faculty directory');
    } finally {
      setLoading(false);
    }
  }, [institution, isAdmin, deptFilter, statusFilter, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // List of members who do not currently have an active faculty profile
  const eligibleMembers = members.filter((m) => {
    const alreadyFaculty = facultyList.some((f) => f.user_id === m.user_id);
    return !alreadyFaculty;
  });

  const openCreateModal = () => {
    setEditingFaculty(null);
    setAddMode('member');
    setSelectedUserId(eligibleMembers.length > 0 ? eligibleMembers[0].user_id : 0);
    setUserEmailInput('');
    setFormDeptId(departments.length > 0 ? departments[0].id : undefined);
    setFormTitle('Professor');
    setFormEmployeeCode('');
    setFormStatus('active');
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (fac: FacultyProfile) => {
    setEditingFaculty(fac);
    setFormDeptId(fac.department_id || undefined);
    setFormTitle(fac.title || 'Professor');
    setFormEmployeeCode(fac.employee_code || '');
    setFormStatus(fac.status || 'active');
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingFaculty) {
        const payload: FacultyProfileUpdatePayload = {
          department_id: formDeptId || null,
          title: formTitle.trim() || null,
          employee_code: formEmployeeCode.trim() || null,
          status: formStatus,
        };
        await api.updateFaculty(institution.id, editingFaculty.id, payload);
      } else {
        const payload: FacultyProfileCreatePayload = {
          department_id: formDeptId || undefined,
          title: formTitle.trim() || undefined,
          employee_code: formEmployeeCode.trim() || undefined,
          status: formStatus,
        };

        if (addMode === 'member') {
          if (!selectedUserId) {
            setFormError('Please select an institution member.');
            setSubmitting(false);
            return;
          }
          payload.user_id = selectedUserId;
        } else {
          if (!userEmailInput.trim()) {
            setFormError('Please enter the user email address.');
            setSubmitting(false);
            return;
          }
          payload.email = userEmailInput.trim();
        }

        await api.createFaculty(institution.id, payload);
      }

      setModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Operation failed. Verify member role and profile.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (fac: FacultyProfile) => {
    if (!institution) return;
    const name = fac.user_name || fac.user_email || `Faculty #${fac.id}`;
    if (!confirm(`Are you sure you want to deactivate faculty profile for "${name}"?`)) {
      return;
    }
    try {
      await api.deleteFaculty(institution.id, fac.id);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to deactivate faculty profile');
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'inactive':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'archived':
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Faculty
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage teaching faculty, instructor assignments, and departmental appointments for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-sm"
          >
            <span>+</span>
            <span>Add Faculty</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] p-3.5 rounded-xl">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search by faculty name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="w-52">
          <CustomSelect
            options={[
              { value: 'all', label: 'All Departments' },
              ...departments.map((d) => ({
                value: String(d.id),
                label: `${d.name} (${d.code})`,
              })),
            ]}
            value={deptFilter}
            onChange={(val) => setDeptFilter(String(val))}
            size="sm"
            searchable
            portalTheme="university"
          />
        </div>

        <div className="w-40">
          <CustomSelect
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'active', label: 'Active' },
              { value: 'inactive', label: 'Inactive' },
              { value: 'archived', label: 'Archived' },
            ]}
            value={statusFilter}
            onChange={(val) => setStatusFilter(String(val))}
            size="sm"
            portalTheme="university"
          />
        </div>

        {(search || deptFilter !== 'all' || statusFilter !== 'all') && (
          <button
            onClick={() => {
              setSearch('');
              setDeptFilter('all');
              setStatusFilter('all');
            }}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition underline ml-auto"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Faculty Table / List */}
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-sm text-[var(--text-muted)]">
            Loading faculty profiles...
          </div>
        ) : facultyList.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-base font-semibold text-[var(--text-primary)]">No faculty found</p>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              {isAdmin
                ? 'Assign an institution member or professor to initialize your faculty directory.'
                : 'No faculty profiles currently exist for this institution.'}
            </p>
            {isAdmin && (
              <button
                onClick={openCreateModal}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
              >
                <span>+</span>
                <span>Add Faculty Member</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border-color)] bg-[var(--bg-primary)]/50 text-[var(--text-secondary)] text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3 font-semibold">Faculty Member</th>
                  <th className="px-5 py-3 font-semibold">Title / Rank</th>
                  <th className="px-5 py-3 font-semibold">Department</th>
                  <th className="px-5 py-3 font-semibold">Employee Code</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  {isAdmin && <th className="px-5 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)] text-[var(--text-primary)]">
                {facultyList.map((fac) => (
                  <tr
                    key={fac.id}
                    className="hover:bg-[var(--bg-primary)]/40 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-[var(--text-primary)]">
                        {fac.user_name || 'Academic Faculty'}
                      </div>
                      <div className="text-xs text-[var(--text-muted)] mt-0.5">
                        {fac.user_email || `User #${fac.user_id}`}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {fac.title || 'Professor'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                      {fac.department_name ? (
                        <div>
                          <span>{fac.department_name}</span>
                          {fac.department_code && (
                            <span className="text-xs text-[var(--text-muted)] ml-1">
                              ({fac.department_code})
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)] italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-[var(--text-secondary)] font-mono">
                      {fac.employee_code || '—'}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusBadgeClass(
                          fac.status
                        )}`}
                      >
                        {fac.status}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="px-5 py-3.5 text-right space-x-2">
                        <button
                          onClick={() => openEditModal(fac)}
                          className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-indigo-400 hover:border-indigo-500/50 transition"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(fac)}
                          className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-red-400 hover:border-red-500/50 transition"
                        >
                          Deactivate
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Create or Edit Faculty */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">
                {editingFaculty ? 'Edit Faculty Profile' : 'Add Faculty Member'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 text-xs rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {!editingFaculty && (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Target Member Selection
                  </label>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1.5 text-xs text-[var(--text-primary)] cursor-pointer">
                      <input
                        type="radio"
                        name="addMode"
                        checked={addMode === 'member'}
                        onChange={() => setAddMode('member')}
                        className="accent-indigo-500"
                      />
                      Select Member
                    </label>
                    <label className="flex items-center gap-1.5 text-xs text-[var(--text-primary)] cursor-pointer">
                      <input
                        type="radio"
                        name="addMode"
                        checked={addMode === 'email'}
                        onChange={() => setAddMode('email')}
                        className="accent-indigo-500"
                      />
                      Enter Email
                    </label>
                  </div>

                  {addMode === 'member' ? (
                    <div>
                      <CustomSelect
                        options={
                          eligibleMembers.length === 0
                            ? [{ value: '0', label: 'No eligible members without faculty profile', disabled: true }]
                            : eligibleMembers.map((m) => ({
                                value: String(m.user_id),
                                label: `${m.user_name || m.user_email} (${m.user_email})`,
                                sublabel: `Role: ${m.role}`,
                              }))
                        }
                        value={selectedUserId ? String(selectedUserId) : '0'}
                        onChange={(val) => setSelectedUserId(Number(val))}
                        searchable
                        portalTheme="university"
                      />
                      <p className="text-[11px] text-[var(--text-muted)] mt-1">
                        Select an existing institution member. Their role will automatically be verified or elevated to professor.
                      </p>
                    </div>
                  ) : (
                    <div>
                      <input
                        type="email"
                        placeholder="professor@university.edu"
                        value={userEmailInput}
                        onChange={(e) => setUserEmailInput(e.target.value)}
                        className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <p className="text-[11px] text-[var(--text-muted)] mt-1">
                        Must belong to a registered user who is an active member of this institution.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {editingFaculty && (
                <div className="p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)]">
                  <p className="text-xs text-[var(--text-muted)]">Faculty Member</p>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {editingFaculty.user_name || editingFaculty.user_email}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)]">{editingFaculty.user_email}</p>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Academic Title / Rank
                </label>
                <input
                  type="text"
                  placeholder="e.g. Associate Professor, Lecturer, Dean"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-[var(--text-secondary)]">Department</label>
                <CustomSelect
                  options={[
                    { value: '', label: 'None / Interdisciplinary' },
                    ...departments.map((d) => ({
                      value: String(d.id),
                      label: `${d.name} (${d.code})`,
                    })),
                  ]}
                  value={formDeptId ? String(formDeptId) : ''}
                  onChange={(val) =>
                    setFormDeptId(val ? Number(val) : undefined)
                  }
                  searchable
                  portalTheme="university"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Employee Code
                  </label>
                  <input
                    type="text"
                    placeholder="FAC-1004"
                    value={formEmployeeCode}
                    onChange={(e) => setFormEmployeeCode(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">Status</label>
                  <CustomSelect
                    options={[
                      { value: 'active', label: 'Active' },
                      { value: 'inactive', label: 'Inactive' },
                      { value: 'archived', label: 'Archived' },
                    ]}
                    value={formStatus}
                    onChange={(val) => setFormStatus(String(val))}
                    portalTheme="university"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-color)]">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingFaculty ? 'Save Changes' : 'Create Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
