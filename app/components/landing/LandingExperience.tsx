"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRightIcon,
  ArrowDownIcon,
  CheckIcon,
  SunIcon,
  MoonIcon,
  AcademicCapIcon,
  CalendarDaysIcon,
  LockClosedIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline";
import { useThemeContext } from "@/context/ThemeContext";
import CampusView from "./CampusView";
import { motion } from "framer-motion";
import { useCampusReducedMotion } from "./useCampusPreferences";
import type { CampusRole } from "./campus-model";
import "./landing.css";

const roles = [
  {
    id: "student" as const,
    label: "Student",
    eyebrow: "A little more room for you",
    title: "Know your classes.\nMake time for your plans.",
    description:
      "See the classes you belong to, explore your subjects, and bring tasks and study time into the same week.",
    points: [
      "Published class events in your calendar",
      "Subject credits and professor profiles, where supplied",
      "Study plans you can review before applying",
    ],
    note: "Official classes are managed by authorised university staff.",
    place: "Library & study spaces",
  },
  {
    id: "professor" as const,
    label: "Professor",
    eyebrow: "From the lecture to the next idea",
    title: "Your teaching,\nwith the full picture.",
    description:
      "See assigned lectures, record what has been delivered, and organise preparation, grading, and your own commitments.",
    points: [
      "Teaching schedules and recorded lecture progress",
      "Drafts, published events, and class announcements",
      "Private tasks alongside your official commitments",
    ],
    note: "Teaching actions follow your verified role and subject assignments.",
    place: "Teaching & seminar rooms",
  },
  {
    id: "administration" as const,
    label: "University administration",
    eyebrow: "A shared foundation for campus",
    title: "Coordinate the campus.\nRespect the individual.",
    description:
      "Connect academic records, teaching assignments, rooms, and timetables through your university’s administration workspace.",
    points: [
      "University users, subjects, sections, and terms",
      "Timetable drafts, impact review, and publication",
      "Academic audit history and official teaching load",
    ],
    note: "University administration does not grant access to personal tasks.",
    place: "Academic administration",
  },
];
const steps = [
  [
    "01",
    "A shared starting point.",
    "Authorised university staff organise academic records and publish official timetables.",
  ],
  [
    "02",
    "Teaching takes shape.",
    "Assigned professors manage class events, announcements, and recorded lecture outcomes.",
  ],
  [
    "03",
    "The right classes, together.",
    "Enrolled learners see relevant published events and subject information in their workspace.",
  ],
  [
    "04",
    "Room for the rest of life.",
    "Personal tasks, study sessions, and work shifts sit around those shared commitments.",
  ],
];
const faqs = [
  [
    "How do I get access?",
    "Sign in with your existing account. If you are new, account creation is available through Sign up. University membership, teaching access, and administration permissions are assigned separately by authorised university staff; creating an account does not grant those roles.",
  ],
  [
    "Who can change an official class?",
    "Authorised instructors and university staff manage shared class events. Students can view published events in their classes; personal calendar editing does not change the official timetable.",
  ],
  [
    "How do timetable changes appear?",
    "Published updates are included when your workspace fetches the schedule. Check Notifications for relevant changes, and refresh the calendar when needed. Email and push delivery depend on your preferences and the university’s service configuration.",
  ],
  [
    "Does the planner decide my week for me?",
    "You can add tasks and request suggested study plans around existing commitments. Review the proposed options before applying a plan. Official university classes stay university-managed.",
  ],
  [
    "What can the AI assistant help with?",
    "Ask about supported app features and your authorised schedule, or request supported planning and timetable actions. Capabilities depend on your role and configured services. It is not a general autonomous administrator; university timetable changes require authorised review and confirmation.",
  ],
  [
    "Are my personal plans visible to university administrators?",
    "Personal tasks, work shifts, and private calendar events are scoped to their owner. Class events and announcements are shared with the appropriate class members. Academic administration does not provide a view into everyone’s personal plans.",
  ],
];
const previews: Record<string, string[][]> = {
  Classes: [
    [
      "Design foundations",
      "4 credits · Section A",
      "Subject introduction, professor details, and published class events.",
    ],
    [
      "Applied mathematics",
      "3 credits · Section B",
      "Explore your timetable, announcements, and class members.",
    ],
    [
      "Lecture progress",
      "Recorded by teaching staff",
      "Planned, delivered, and remaining lectures are shown separately.",
    ],
  ],
  Planner: [
    [
      "1. Add your tasks",
      "Reading response · Due Friday",
      "Set a deadline and estimated study time.",
    ],
    [
      "2. Review a plan",
      "Suggested study sessions",
      "Compare options around existing commitments.",
    ],
    [
      "3. Choose what fits",
      "Apply your reviewed plan",
      "Keep university classes in place.",
    ],
  ],
  Dashboard: [
    [
      "Today’s schedule",
      "09:00 · Design seminar",
      "Official class · Learning Hall",
    ],
    ["Upcoming deadline", "Reading response · Friday", "Your private task"],
    ["Your classes", "Design foundations", "Open the shared class workspace"],
  ],
};

export default function LandingExperience() {
  const [role, setRole] = useState<CampusRole>("student");
  const [preview, setPreview] = useState("Calendar");
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const { resolvedTheme, toggleTheme } = useThemeContext();
  const selected = roles.find((item) => item.id === role)!;
  const reducedMotion = useCampusReducedMotion();
  return (
    <div className="ss-landing">
      <a className="ss-skip" href="#main">
        Skip to content
      </a>
      <header className="ss-header ss-container">
        <Link href="/" className="ss-brand" aria-label="SyncShift home">
          <span className="ss-brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          SyncShift<span className="ss-brand-dot">.</span>
        </Link>
        <nav aria-label="Main navigation">
          <a href="#how-it-connects">How it connects</a>
          <a href="#your-role">Your workspace</a>
          <a href="#questions">Questions</a>
        </nav>
        <div className="ss-header-actions">
          <button
            className="ss-theme"
            onClick={toggleTheme}
            aria-label={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}
          >
            {resolvedTheme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
          <Link className="ss-button ss-button-small" href="/login">
            Sign in <ArrowRightIcon />
          </Link>
        </div>
      </header>
      <main id="main">
        <section className="ss-hero ss-container" aria-labelledby="hero-title">
          <div className="ss-hero-copy">
            <p className="ss-eyebrow">
              <span /> ONE CAMPUS. CONNECTED DAYS.
            </p>
            <h1 id="hero-title">
              Your university day,
              <br />
              <em>in sync.</em>
            </h1>
            <p className="ss-lead">
              One workspace for university schedules, teaching, and personal
              plans.
            </p>
            <p className="ss-hero-detail">
              From your first class to your next deadline. Find the shared plan,
              and make space for your own.
            </p>
            <div className="ss-actions">
              <Link className="ss-button" href="/login">
                Enter your workspace <ArrowRightIcon />
              </Link>
              <a className="ss-text-link" href="#your-role">
                Find your perspective <ArrowDownIcon />
              </a>
            </div>
            <p className="ss-access-note">
              Students · Professors · University administration
            </p>
          </div>
          <div className="ss-hero-world">
            <div className="ss-orbit ss-orbit-one" />
            <div className="ss-orbit ss-orbit-two" />
            <div className="ss-world-caption">
              <span>THE CONNECTED CAMPUS</span>
              <span>Illustrative scene / 01</span>
            </div>
            <CampusView
              role={role}
              label="Illustrative campus with an academic building, library, courtyard, paths, and trees"
            />
            <div className="ss-world-label">
              <span className="ss-dot" /> A shared timetable. Individual
              possibilities.
            </div>
            <div
              className="ss-floating-schedule"
              aria-label="Illustrative timetable"
            >
              <div>
                <CalendarDaysIcon />
                <strong>A day in balance</strong>
                <span>EXAMPLE</span>
              </div>
              <p>
                <i />
                09:00 <b>Design seminar</b>
                <small>Class</small>
              </p>
              <p>
                <i />
                13:00 <b>Independent study</b>
                <small>Private</small>
              </p>
            </div>
          </div>
        </section>
        <div className="ss-principles ss-container">
          <span>Built around university life</span>
          <p>
            <AcademicCapIcon /> Shared academic schedules
          </p>
          <p>
            <CalendarDaysIcon /> Personal space to plan
          </p>
          <p>
            <LockClosedIcon /> Clear role boundaries
          </p>
        </div>
        <section
          id="how-it-connects"
          className="ss-section ss-container"
          aria-labelledby="connection-title"
        >
          <div className="ss-section-intro">
            <p className="ss-eyebrow">01 / THE CONNECTION</p>
            <h2 id="connection-title">
              A campus moves together.
              <br />
              <span>Everyone has their own day.</span>
            </h2>
            <p>
              One shared academic foundation. Different responsibilities,
              connected through the same platform.
            </p>
          </div>
          <div className="ss-story">
            {steps.map(([number, title, text]) => (
              <motion.article
                key={number}
                initial={{ y: reducedMotion ? 0 : 16 }}
                whileInView={{ y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: reducedMotion ? 0 : 0.45 }}
              >
                <span className="ss-step-number">{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </motion.article>
            ))}
          </div>
          <p className="ss-fineprint">
            Published changes are reflected when schedules refresh.
            Notifications help you keep track.
          </p>
        </section>
        <section
          id="your-role"
          className="ss-role-section"
          aria-labelledby="role-title"
        >
          <div className="ss-container">
            <div className="ss-section-intro">
              <p className="ss-eyebrow">02 / YOUR PERSPECTIVE</p>
              <h2 id="role-title">
                One platform.
                <br />
                <span>Your kind of workspace.</span>
              </h2>
            </div>
            <div
              className="ss-role-tabs"
              role="tablist"
              aria-label="Explore university roles"
            >
              {roles.map((item, index) => (
                <button
                  key={item.id}
                  ref={(node) => {
                    buttons.current[index] = node;
                  }}
                  id={`role-${item.id}`}
                  role="tab"
                  type="button"
                  aria-selected={role === item.id}
                  aria-controls="role-panel"
                  tabIndex={role === item.id ? 0 : -1}
                  onClick={() => setRole(item.id)}
                  onKeyDown={(event) => {
                    const offset =
                      event.key === "ArrowRight"
                        ? 1
                        : event.key === "ArrowLeft"
                          ? -1
                          : 0;
                    const next =
                      event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? roles.length - 1
                          : (index + offset + roles.length) % roles.length;
                    if (offset || event.key === "Home" || event.key === "End") {
                      event.preventDefault();
                      setRole(roles[next].id);
                      buttons.current[next]?.focus();
                    }
                  }}
                >
                  {item.label}
                  <ArrowRightIcon />
                </button>
              ))}
            </div>
            <div
              id="role-panel"
              className="ss-role-panel"
              role="tabpanel"
              aria-labelledby={`role-${role}`}
              tabIndex={0}
            >
              <div className="ss-role-copy">
                <p className="ss-eyebrow">{selected.eyebrow}</p>
                <h3>{selected.title}</h3>
                <p>{selected.description}</p>
                <ul>
                  {selected.points.map((point) => (
                    <li key={point}>
                      <CheckIcon />
                      {point}
                    </li>
                  ))}
                </ul>
                <p className="ss-role-note">
                  <LockClosedIcon />
                  {selected.note}
                </p>
              </div>
              <div className="ss-role-map">
                <CampusView
                  role={role}
                  label="Illustrative campus with an academic building, library, courtyard, paths, and trees"
                />
                <span className="ss-map-label">
                  <span className="ss-dot" />
                  {selected.place}
                </span>
              </div>
            </div>
          </div>
        </section>
        <section
          id="inside-syncshift"
          className="ss-section ss-container"
          aria-labelledby="preview-title"
        >
          <div className="ss-preview-heading">
            <div>
              <p className="ss-eyebrow">03 / A CLOSER LOOK</p>
              <h2 id="preview-title">
                Less scattered.
                <br />
                <span>More in view.</span>
              </h2>
            </div>
            <p>
              A familiar place for the details of your day.
              <br />
              Synthetic examples based on the current app.
            </p>
          </div>
          <div className="ss-product">
            <div className="ss-product-bar">
              <span className="ss-brand">
                SyncShift<span className="ss-brand-dot">.</span>
              </span>
              <span className="ss-example-label">ILLUSTRATIVE WORKSPACE</span>
            </div>
            <div
              className="ss-preview-controls"
              aria-label="Choose product preview"
            >
              {["Dashboard", "Calendar", "Classes", "Planner"].map((label) => (
                <button
                  key={label}
                  aria-pressed={preview === label}
                  onClick={() => setPreview(label)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="ss-product-body" aria-live="polite">
              <div className="ss-product-title">
                <div>
                  <small>YOUR WORKSPACE / {preview.toUpperCase()}</small>
                  <h3>
                    {preview === "Calendar"
                      ? "The week, at a glance."
                      : preview === "Classes"
                        ? "Your learning community."
                        : preview === "Planner"
                          ? "Make room for focused work."
                          : "Your day, in sync."}
                  </h3>
                </div>
                <span className="ss-chip">Example data</span>
              </div>
              {preview === "Calendar" ? (
                <div
                  className="ss-demo-calendar"
                  tabIndex={0}
                  role="region"
                  aria-label="Example weekly calendar, horizontally scrollable"
                >
                  <div className="ss-demo-grid">
                    <div className="ss-time-column">
                      <span>TIME</span>
                      <span>09:00</span>
                      <span>11:00</span>
                      <span>13:00</span>
                      <span>15:00</span>
                    </div>
                    {["MON", "TUE", "WED", "THU", "FRI"].map((day, index) => (
                      <div className="ss-day-column" key={day}>
                        <strong>{day}</strong>
                        <div className={`ss-demo-event ss-event-${index % 3}`}>
                          <small>
                            {index % 2 ? "PRIVATE" : "UNIVERSITY CLASS"}
                          </small>
                          <b>
                            {
                              [
                                "Design seminar",
                                "Reading & notes",
                                "Applied mathematics",
                                "Project preparation",
                                "Design studio",
                              ][index]
                            }
                          </b>
                          <span>
                            {index % 2 ? "Your own plan" : "University-managed"}
                          </span>
                        </div>
                        {index % 2 === 0 && (
                          <div className="ss-demo-event ss-private-event">
                            <small>PRIVATE</small>
                            <b>Independent study</b>
                            <span>Your own plan</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="ss-preview-cards">
                  {previews[preview].map(([title, caption, text]) => (
                    <article key={title}>
                      <span className="ss-preview-icon">
                        <AcademicCapIcon />
                      </span>
                      <h4>{title}</h4>
                      <strong>{caption}</strong>
                      <p>{text}</p>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="ss-ai-note">
            <SparklesIcon />
            <div>
              <h3>A little guidance, right where you plan.</h3>
              <p>
                Ask SyncShift about your authorised schedule, supported planning
                actions, or how to use the app. AI capabilities depend on your
                role and configured services.
              </p>
            </div>
            <span>SYNCSHIFT ASSISTANT</span>
          </div>
        </section>
        <section
          className="ss-privacy ss-container"
          aria-labelledby="privacy-title"
        >
          <div>
            <p className="ss-eyebrow">04 / CLEAR BOUNDARIES</p>
            <h2 id="privacy-title">
              Shared where it matters.
              <br />
              <span>Private where it should be.</span>
            </h2>
            <p>
              Your university’s timetable connects the campus. Your personal
              plans stay your own.
            </p>
          </div>
          <div className="ss-boundaries">
            <article>
              <AcademicCapIcon />
              <h3>Shared with your class</h3>
              <p>
                Published class events, announcements, and relevant subject
                information.
              </p>
            </article>
            <article>
              <LockClosedIcon />
              <h3>Personal to you</h3>
              <p>
                Your tasks, work shifts, and private calendar events.
                Administration access does not open these to other users.
              </p>
            </article>
          </div>
        </section>
        <section
          id="questions"
          className="ss-section ss-container ss-faq"
          aria-labelledby="faq-title"
        >
          <div>
            <p className="ss-eyebrow">A FEW THINGS TO KNOW</p>
            <h2 id="faq-title">
              Before your
              <br />
              <span>next chapter.</span>
            </h2>
          </div>
          <div>
            {faqs.map(([question, answer]) => (
              <details key={question}>
                <summary>
                  {question}
                  <span aria-hidden="true">+</span>
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>
        <section className="ss-final ss-container">
          <span className="ss-eyebrow">MAKE SPACE FOR YOUR UNIVERSITY DAY</span>
          <h2>
            A shared campus.
            <br />
            <em>A day that’s yours.</em>
          </h2>
          <Link className="ss-button" href="/login">
            Sign in to SyncShift <ArrowRightIcon />
          </Link>
          <p>
            New here? <Link href="/signup">Create an account</Link>. University
            access is assigned separately.
          </p>
        </section>
      </main>
      <footer className="ss-footer ss-container">
        <Link href="/" className="ss-brand">
          SyncShift<span className="ss-brand-dot">.</span>
        </Link>
        <p>University life, thoughtfully connected.</p>
        <nav aria-label="Footer">
          <a href="#your-role">Explore roles</a>
          <a href="#questions">Questions</a>
          <Link href="/login">
            Sign in <ArrowRightIcon />
          </Link>
        </nav>
      </footer>
    </div>
  );
}
