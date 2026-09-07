'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, CourseOut, CourseCreatePayload, BlockCreatePayload, BlockOut } from '@/lib/api';
import { useCalendar } from '@/context/CalendarContext';

export function useAddBlock() {
  const { addBlock, updateBlock } = useCalendar();

  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(false);

  const fetchCourses = useCallback(async () => {
    setCoursesLoading(true);
    try {
      const data = await api.getCourses();
      setCourses(data || []);
    } catch {
      setCourses([]);
    } finally {
      setCoursesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  const createCourse = async (payload: CourseCreatePayload): Promise<CourseOut> => {
    const created = await api.createCourse(payload);
    setCourses((prev) => [...prev, created]);
    return created;
  };

  const submitBlock = async (
    payload: BlockCreatePayload,
    editId?: number
  ): Promise<BlockOut> => {
    if (editId !== undefined) {
      return updateBlock(editId, payload);
    }
    return addBlock(payload);
  };

  return { courses, coursesLoading, fetchCourses, createCourse, submitBlock };
}
