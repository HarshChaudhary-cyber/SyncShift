'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import {
  api,
  Room,
  RoomCreatePayload,
  RoomUpdatePayload,
} from '@/lib/api';

const ROOM_TYPES = [
  { value: 'classroom', label: 'Classroom' },
  { value: 'lecture_hall', label: 'Lecture Hall' },
  { value: 'laboratory', label: 'Laboratory' },
  { value: 'seminar_room', label: 'Seminar Room' },
  { value: 'auditorium', label: 'Auditorium' },
  { value: 'other', label: 'Other / Multi-purpose' },
];

export default function RoomsPage() {
  const { institution, isAdmin } = useUniversity();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [buildingFilter, setBuildingFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Create / Edit Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [form, setForm] = useState<RoomCreatePayload>({
    building: '',
    room_number: '',
    name: '',
    capacity: 40,
    room_type: 'classroom',
    description: '',
    basic_features: '',
    status: 'active',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRooms(institution.id, {
        building: buildingFilter !== 'all' ? buildingFilter : undefined,
        room_type: typeFilter !== 'all' ? typeFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setRooms(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load rooms');
    } finally {
      setLoading(false);
    }
  }, [institution, buildingFilter, typeFilter, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Derive unique buildings from the full set or current set for filtering
  const availableBuildings = useMemo(() => {
    const set = new Set<string>();
    rooms.forEach((r) => {
      if (r.building) set.add(r.building);
    });
    return Array.from(set).sort();
  }, [rooms]);

  // Client-side search filtering by building, room_number, name
  const filteredRooms = useMemo(() => {
    if (!search.trim()) return rooms;
    const s = search.toLowerCase();
    return rooms.filter(
      (r) =>
        r.building.toLowerCase().includes(s) ||
        r.room_number.toLowerCase().includes(s) ||
        (r.name && r.name.toLowerCase().includes(s)) ||
        (r.basic_features && r.basic_features.toLowerCase().includes(s))
    );
  }, [rooms, search]);

  const openCreateModal = () => {
    setEditingRoom(null);
    setForm({
      building: '',
      room_number: '',
      name: '',
      capacity: 40,
      room_type: 'classroom',
      description: '',
      basic_features: '',
      status: 'active',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (room: Room) => {
    setEditingRoom(room);
    setForm({
      building: room.building,
      room_number: room.room_number,
      name: room.name || '',
      capacity: room.capacity,
      room_type: room.room_type || 'classroom',
      description: room.description || '',
      basic_features: room.basic_features || '',
      status: room.status || 'active',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution) return;

    if (!form.building.trim() || !form.room_number.trim()) {
      setFormError('Building and room number are required.');
      return;
    }
    if (form.capacity <= 0) {
      setFormError('Room capacity must be at least 1 seat.');
      return;
    }

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingRoom) {
        const payload: RoomUpdatePayload = {
          building: form.building.trim(),
          room_number: form.room_number.trim(),
          name: form.name?.trim() || null,
          capacity: Number(form.capacity),
          room_type: form.room_type,
          description: form.description?.trim() || null,
          basic_features: form.basic_features?.trim() || null,
          status: form.status,
        };
        await api.updateRoom(institution.id, editingRoom.id, payload);
      } else {
        const payload: RoomCreatePayload = {
          building: form.building.trim(),
          room_number: form.room_number.trim(),
          name: form.name?.trim() || undefined,
          capacity: Number(form.capacity),
          room_type: form.room_type,
          description: form.description?.trim() || undefined,
          basic_features: form.basic_features?.trim() || undefined,
          status: form.status,
        };
        await api.createRoom(institution.id, payload);
      }

      setModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error
          ? err.message
          : 'Operation failed. Room number may already exist in this building.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (room: Room) => {
    if (!institution) return;
    const label = `${room.building} ${room.room_number}${room.name ? ` (${room.name})` : ''}`;
    if (!confirm(`Are you sure you want to archive room "${label}"?`)) {
      return;
    }
    try {
      await api.deleteRoom(institution.id, room.id);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to archive room');
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'maintenance':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'archived':
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
    }
  };

  const formatRoomType = (type: string) => {
    const found = ROOM_TYPES.find((t) => t.value === type);
    return found ? found.label : type.replace('_', ' ');
  };

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Rooms
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage classrooms, lecture halls, and laboratory spaces with seating capacities for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-sm"
          >
            <span>+</span>
            <span>Add Room</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] p-3.5 rounded-xl">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search building, room #, or features..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-[var(--text-muted)]">Building:</label>
          <select
            value={buildingFilter}
            onChange={(e) => setBuildingFilter(e.target.value)}
            className="px-2.5 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Buildings</option>
            {availableBuildings.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-[var(--text-muted)]">Type:</label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2.5 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Room Types</option>
            {ROOM_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-[var(--text-muted)]">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="maintenance">Maintenance</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {(search || buildingFilter !== 'all' || typeFilter !== 'all' || statusFilter !== 'all') && (
          <button
            onClick={() => {
              setSearch('');
              setBuildingFilter('all');
              setTypeFilter('all');
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

      {/* Rooms Table */}
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-sm text-[var(--text-muted)]">
            Loading rooms & resources...
          </div>
        ) : filteredRooms.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-base font-semibold text-[var(--text-primary)]">No rooms found</p>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              {isAdmin
                ? 'Add classrooms, lecture halls, and laboratories for academic timetabling.'
                : 'No rooms configured for this institution.'}
            </p>
            {isAdmin && (
              <button
                onClick={openCreateModal}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
              >
                <span>+</span>
                <span>Add Room</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border-color)] bg-[var(--bg-primary)]/50 text-[var(--text-secondary)] text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3 font-semibold">Location</th>
                  <th className="px-5 py-3 font-semibold">Type</th>
                  <th className="px-5 py-3 font-semibold text-center">Capacity</th>
                  <th className="px-5 py-3 font-semibold">Equipment / Features</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  {isAdmin && <th className="px-5 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)] text-[var(--text-primary)]">
                {filteredRooms.map((room) => (
                  <tr
                    key={room.id}
                    className="hover:bg-[var(--bg-primary)]/40 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-[var(--text-primary)]">
                        {room.building} {room.room_number}
                      </div>
                      {room.name && (
                        <div className="text-xs text-[var(--text-muted)] mt-0.5">
                          {room.name}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 capitalize">
                        {formatRoomType(room.room_type)}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {room.capacity} seats
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-[var(--text-secondary)] max-w-xs truncate">
                      {room.basic_features || (
                        <span className="text-[var(--text-muted)] italic">Standard setup</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${getStatusBadgeClass(
                          room.status
                        )}`}
                      >
                        {room.status}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="px-5 py-3.5 text-right space-x-2">
                        <button
                          onClick={() => openEditModal(room)}
                          className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-indigo-400 hover:border-indigo-500/50 transition"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(room)}
                          className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-red-400 hover:border-red-500/50 transition"
                        >
                          Archive
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

      {/* Modal: Create or Edit Room */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">
                {editingRoom ? 'Edit Room' : 'Add Physical Room'}
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
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Building <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Science Hall, Block B"
                    value={form.building}
                    onChange={(e) => setForm({ ...form, building: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Room Number <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 101, A-204"
                    value={form.room_number}
                    onChange={(e) => setForm({ ...form, room_number: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Display / Common Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Alan Turing Auditorium"
                  value={form.name || ''}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Room Type
                  </label>
                  <select
                    value={form.room_type || 'classroom'}
                    onChange={(e) => setForm({ ...form, room_type: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500 capitalize"
                  >
                    {ROOM_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Capacity (Seats) <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={form.capacity}
                    onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Basic Features / Equipment
                </label>
                <input
                  type="text"
                  placeholder="e.g. Projector, Whiteboard, 30 PC Workstations, Audio System"
                  value={form.basic_features || ''}
                  onChange={(e) => setForm({ ...form, basic_features: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">Status</label>
                  <select
                    value={form.status || 'active'}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="active">Active</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-[var(--text-secondary)]">
                    Description / Notes
                  </label>
                  <input
                    type="text"
                    placeholder="Floor 2 east wing..."
                    value={form.description || ''}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                  {submitting ? 'Saving...' : editingRoom ? 'Save Changes' : 'Create Room'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
