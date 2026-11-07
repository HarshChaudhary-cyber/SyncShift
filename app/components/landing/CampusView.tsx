"use client";

import {
  Component,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import dynamic from "next/dynamic";
import CampusIllustration from "./CampusIllustration";
import type { CampusRole } from "./campus-model";
import { useCampusReducedMotion } from "./useCampusPreferences";

const CampusScene = dynamic(() => import("./CampusScene"), { ssr: false });

class SceneBoundary extends Component<
  { children: ReactNode; onFailure: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFailure();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export default function CampusView({
  role,
  label,
}: {
  role: CampusRole;
  label: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [seen, setSeen] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const [compact, setCompact] = useState(true);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [staticView, setStaticView] = useState(false);
  const reduced = useCampusReducedMotion();
  const onReady = useCallback(() => setReady(true), []);
  const onFailure = useCallback(() => {
    setFailed(true);
    setReady(false);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(entry.isIntersecting);
        if (entry.isIntersecting) setSeen(true);
      },
      { threshold: 0.05 },
    );
    if (container.current) observer.observe(container.current);
    const update = () => setPageVisible(!document.hidden);
    const media = window.matchMedia("(max-width: 780px)");
    const resize = () =>
      setCompact(media.matches || navigator.hardwareConcurrency <= 4);
    resize();
    update();
    document.addEventListener("visibilitychange", update);
    media.addEventListener("change", resize);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", update);
      media.removeEventListener("change", resize);
    };
  }, []);

  const showScene = seen && !failed && !staticView;
  const active = visible && pageVisible;
  return (
    <div
      ref={container}
      className="ss-campus-view"
      data-renderer={showScene && ready ? "webgl" : "static"}
      data-motion={reduced ? "reduced" : "normal"}
      data-active={active}
    >
      <div
        className={`ss-static-campus ${showScene && ready && active ? "ss-static-hidden" : ""}`}
        role="img"
        aria-label={label}
      >
        <CampusIllustration role={role} />
      </div>
      {showScene && (
        <div className="ss-webgl-campus" aria-hidden="true">
          <SceneBoundary onFailure={onFailure}>
            <CampusScene
              role={role}
              active={active}
              reduced={reduced}
              compact={compact}
              onReady={onReady}
              onFailure={onFailure}
            />
          </SceneBoundary>
        </div>
      )}
      <div className="ss-scene-controls">
        <span>
          {failed
            ? "Campus illustration"
            : showScene && ready
              ? "3D campus"
              : "Campus illustration"}
        </span>
        <button
          type="button"
          aria-pressed={staticView}
          disabled={failed}
          onClick={() => {
            setStaticView(!staticView);
            setReady(false);
          }}
        >
          {staticView ? "Explore in 3D" : "Use static view"}
        </button>
      </div>
    </div>
  );
}
