export type Lecture = {event_key:string; date:string; start_time:string; end_time:string; title:string; minutes:number; status:string; class_id?:number; class_name?:string};
export type Subject = {
  subject:{name:string; code:string|null; credits:number|null; department:string|null; introduction:string|null; term:string|null; section:string|null};
  professors:{user_id:number; name:string}[];
  progress:{planned_lectures:number; planned_hours:number; delivered_lectures:number; delivered_hours:number; remaining_lectures:number; remaining_hours:number};
  sessions:Lecture[];
};
export type Teaching = {today:string; timezone:string; classes:(Subject & {id:number;name:string})[]; today_sessions:Lecture[]; upcoming:Lecture[]; completed_today:number; remaining_today:number};
export type Profile = {user_id:number; name:string; avatar_url?:string; introduction:string; email?:string; university_email?:string; timezone?:string;
  enrollments?:{subject:string;section:string;term:string}[];
  affiliations:{institution:string;institution_id:number;department:string;designation:string;staff_identifier?:string}[];
  subjects:{id:number;name:string}[]; academic?:{university:string;department:string;enrollment_number:string;program:string;year:number}[];
  professional:Record<string,string>;
};
export type Appointment = {id?:number; title:string;location:string;event_date:string;start_time:string;end_time:string;class_ids:number[]};
export const isProfessor = (role?:string|null) => ['faculty','professor'].includes(role || '');
