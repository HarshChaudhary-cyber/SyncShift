"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Group, OrthographicCamera } from "three";
import {
  campusParts,
  campusTrees,
  roleColors,
  type CampusRole,
} from "./campus-model";

type SceneProps = {
  role: CampusRole;
  active: boolean;
  reduced: boolean;
  compact: boolean;
  onReady: () => void;
  onFailure: () => void;
};

function Campus({
  role,
  reduced,
  compact,
  onReady,
  onFailure,
}: Omit<SceneProps, "active">) {
  const group = useRef<Group>(null);
  const ready = useRef(false);
  const { camera, size, invalidate, gl } = useThree();
  const angle = reduced
    ? -0.12
    : role === "student"
      ? -0.12
      : role === "professor"
        ? 0.08
        : -0.28;

  useLayoutEffect(() => {
    if (camera instanceof OrthographicCamera) {
      camera.zoom = Math.min(size.width / 14.8, size.height / 11.8);
      camera.position.set(10, 10, 13);
      camera.lookAt(0, 0.3, 0);
      camera.updateProjectionMatrix();
      invalidate();
    }
  }, [camera, size.width, size.height, invalidate]);
  useEffect(() => {
    invalidate();
  }, [role, reduced, invalidate]);
  useEffect(() => {
    const lost = (event: Event) => {
      event.preventDefault();
      onFailure();
    };
    gl.domElement.addEventListener("webglcontextlost", lost);
    return () => gl.domElement.removeEventListener("webglcontextlost", lost);
  }, [gl, onFailure]);
  useFrame((_, delta) => {
    if (!ready.current) {
      ready.current = true;
      onReady();
    }
    if (!group.current) return;
    const difference = angle - group.current.rotation.y;
    group.current.rotation.y = reduced
      ? angle
      : group.current.rotation.y +
        difference * (1 - Math.exp(-Math.min(delta, 0.05) * 7));
    if (!reduced && Math.abs(difference) > 0.0005) invalidate();
  });

  return (
    <group ref={group} rotation={[0, -0.12, 0]}>
      {campusParts.map((part, i) => (
        <mesh key={i} position={part.position} scale={part.size}>
          <boxGeometry />
          <meshStandardMaterial
            color={part.highlight === role ? roleColors[role] : part.color}
            roughness={0.8}
            metalness={0.03}
          />
        </mesh>
      ))}
      {campusTrees
        .filter((_, i) => !compact || i % 2 === 0)
        .map(([x, , z], i) => (
          <group key={i} position={[x, 0, z]}>
            <mesh
              position={[0.15, 0.075, 0.05]}
              rotation={[-Math.PI / 2, 0, 0]}
              scale={[0.6, 0.4, 1]}
            >
              <circleGeometry args={[1, 12]} />
              <meshBasicMaterial
                color="#57536d"
                transparent
                opacity={0.18}
                depthWrite={false}
              />
            </mesh>
            <mesh position={[0, 0.4, 0]}>
              <cylinderGeometry args={[0.055, 0.075, 0.8, 6]} />
              <meshStandardMaterial color="#766779" />
            </mesh>
            <mesh position={[0, 1, 0]} scale={[0.42, 0.64, 0.42]}>
              <icosahedronGeometry args={[1, compact ? 0 : 1]} />
              <meshStandardMaterial
                color={i % 2 ? "#8daa9c" : "#709589"}
                roughness={1}
              />
            </mesh>
          </group>
        ))}
      {/* A low-cost painted courtyard inset; no expensive shadow maps or postprocessing. */}
      <mesh position={[0, 0.095, 1]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.52, 0.57, 40]} />
        <meshBasicMaterial color="#9580c8" />
      </mesh>
    </group>
  );
}

export default function CampusScene(props: SceneProps) {
  return (
    <Canvas
      orthographic
      camera={{ position: [10, 10, 13], zoom: 35, near: 0.1, far: 100 }}
      dpr={props.compact ? 1 : [1, 1.5]}
      frameloop={props.active ? "demand" : "never"}
      gl={{
        alpha: true,
        antialias: !props.compact,
        powerPreference: "low-power",
      }}
      fallback={
        <span className="ss-canvas-unavailable">
          Static campus illustration
        </span>
      }
    >
      <ambientLight intensity={1.6} />
      <directionalLight position={[-5, 9, 5]} intensity={2.5} color="#fff1e8" />
      <directionalLight position={[5, 4, -6]} intensity={1.4} color="#aea6ff" />
      <Campus {...props} />
    </Canvas>
  );
}
