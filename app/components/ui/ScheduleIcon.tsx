import {
  AcademicCapIcon, ArrowPathIcon, ArrowPathRoundedSquareIcon, BellIcon,
  BoltIcon, BookOpenIcon, BriefcaseIcon, BuildingOfficeIcon, CalendarDaysIcon,
  CheckCircleIcon, ClockIcon, CurrencyDollarIcon, DocumentTextIcon,
  ExclamationCircleIcon, ExclamationTriangleIcon, InformationCircleIcon,
  MapPinIcon, MinusIcon, PencilSquareIcon, PlusIcon, SparklesIcon, UserIcon,
  MoonIcon, TrashIcon, DocumentDuplicateIcon, Cog6ToothIcon,
} from '@heroicons/react/24/outline';

const icons = {
  academic: AcademicCapIcon, repeat: ArrowPathIcon, biweekly: ArrowPathRoundedSquareIcon,
  notification: BellIcon, quick: BoltIcon, study: BookOpenIcon, work: BriefcaseIcon,
  building: BuildingOfficeIcon, calendar: CalendarDaysIcon, complete: CheckCircleIcon,
  time: ClockIcon, earnings: CurrencyDollarIcon, document: DocumentTextIcon,
  conflict: ExclamationCircleIcon, warning: ExclamationTriangleIcon,
  info: InformationCircleIcon, location: MapPinIcon, remove: MinusIcon,
  task: PencilSquareIcon, add: PlusIcon, assistant: SparklesIcon, professor: UserIcon,
  night: MoonIcon, delete: TrashIcon, duplicate: DocumentDuplicateIcon, settings: Cog6ToothIcon,
};

/** Decorative outline icon; the adjacent text provides the accessible label. */
export default function ScheduleIcon({ name }: { name: keyof typeof icons }) {
  const Icon = icons[name];
  return <Icon aria-hidden="true" focusable="false" style={{
    display: 'inline-block', width: '1em', height: '1em',
    verticalAlign: '-0.15em', flexShrink: 0,
  }} />;
}
