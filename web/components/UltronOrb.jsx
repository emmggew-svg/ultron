"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/* ---------- Shaders ---------- */

const vertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aSeed;
  attribute vec3 aColor;
  uniform float uTime;
  uniform float uPixelRatio;
  uniform float uPulse;
  uniform float uMode; // 0 = core, 1 = cloud
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    float t = uTime;

    if (uMode < 0.5) {
      // Core: breathing + shimmering surface
      float r = length(p);
      vec3 n = normalize(p);
      float wobble = sin(t * 1.6 + aSeed * 40.0 + r * 3.0) * 0.035;
      p += n * (wobble + uPulse * 0.06);
    } else {
      // Cloud: slow turbulent drift
      p.x += sin(t * 0.35 + aSeed * 30.0) * 0.18;
      p.y += cos(t * 0.30 + aSeed * 22.0) * 0.18;
      p.z += sin(t * 0.28 + aSeed * 17.0) * 0.18;
    }

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;

    float twinkle = 0.65 + 0.35 * sin(t * 2.0 + aSeed * 60.0);
    gl_PointSize = aSize * uPixelRatio * (260.0 / -mv.z) * (0.8 + uPulse * 0.25);

    vColor = aColor * (0.8 + 0.5 * twinkle);
    vAlpha = twinkle;
  }
`;

const fragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float d = length(uv);
    if (d > 0.5) discard;
    float core = smoothstep(0.5, 0.0, d);
    float glow = pow(core, 2.2);
    gl_FragColor = vec4(vColor * (0.5 + glow * 1.6), glow * vAlpha);
  }
`;

/* ---------- Helpers ---------- */

const PALETTE = [
  new THREE.Color("#ff1a00"), // deep red
  new THREE.Color("#ff3d00"), // red-orange
  new THREE.Color("#ff6a00"), // orange
  new THREE.Color("#ff9a2e"), // light orange
  new THREE.Color("#ffd27a"), // hot highlight
];

function pickColor(heat) {
  // heat 0..1 -> palette index with some randomness
  const f = Math.min(0.999, Math.max(0, heat + (Math.random() - 0.5) * 0.25));
  const i = Math.floor(f * (PALETTE.length - 1));
  const a = PALETTE[i];
  const b = PALETTE[i + 1];
  return a.clone().lerp(b, Math.random());
}

function randomOnSphere(radius) {
  const u = Math.random();
  const v = Math.random();
  const theta = 2 * Math.PI * u;
  const phi = Math.acos(2 * v - 1);
  return new THREE.Vector3(
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.sin(phi) * Math.sin(theta),
    radius * Math.cos(phi)
  );
}

function buildGeometry(count, generator) {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const seeds = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    const { pos, color, size } = generator(i);
    positions.set([pos.x, pos.y, pos.z], i * 3);
    colors.set([color.r, color.g, color.b], i * 3);
    sizes[i] = size;
    seeds[i] = Math.random();
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
  geo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
  return geo;
}

function makeMaterial(mode, pixelRatio) {
  return new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uTime: { value: 0 },
      uPulse: { value: 0 },
      uMode: { value: mode },
      uPixelRatio: { value: pixelRatio },
    },
  });
}

/* ---------- Component ---------- */

export default function UltronOrb() {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const isMobile = window.innerWidth < 768;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030102, 0.035);

    const camera = new THREE.PerspectiveCamera(
      55,
      mount.clientWidth / mount.clientHeight,
      0.1,
      200
    );
    camera.position.set(0, 0, isMobile ? 12 : 9.5);

    const renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(pixelRatio);
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const root = new THREE.Group();
    scene.add(root);

    const scale = isMobile ? 0.6 : 1;
    const CORE_COUNT = Math.floor(14000 * scale);
    const HALO_COUNT = Math.floor(5000 * scale);
    const CLOUD_COUNT = Math.floor(16000 * scale);
    const RING_COUNT = Math.floor(7000 * scale);
    const STREAM_COUNT = Math.floor(5000 * scale);

    /* 1. Core: dense glowing sphere (shell + volume, hotter in the middle) */
    const coreGeo = buildGeometry(CORE_COUNT, () => {
      const shell = Math.random() < 0.55;
      const radius = shell
        ? 1.65 + (Math.random() - 0.5) * 0.06
        : 1.65 * Math.cbrt(Math.random());
      const pos = randomOnSphere(radius);
      const heat = 1 - radius / 1.7;
      return {
        pos,
        color: pickColor(heat * 0.9 + (shell ? 0.0 : 0.1)),
        size: shell ? 0.9 + Math.random() * 0.9 : 0.6 + Math.random() * 0.8,
      };
    });
    const coreMat = makeMaterial(0, pixelRatio);
    const core = new THREE.Points(coreGeo, coreMat);
    root.add(core);

    /* 2. Halo: loose particles hugging the sphere */
    const haloGeo = buildGeometry(HALO_COUNT, () => {
      const radius = 1.8 + Math.pow(Math.random(), 1.8) * 1.6;
      return {
        pos: randomOnSphere(radius),
        color: pickColor(0.2 + Math.random() * 0.4),
        size: 0.5 + Math.random() * 1.1,
      };
    });
    const haloMat = makeMaterial(1, pixelRatio);
    const halo = new THREE.Points(haloGeo, haloMat);
    root.add(halo);

    /* 3. Big cloud: particles everywhere around the orb */
    const cloudGeo = buildGeometry(CLOUD_COUNT, () => {
      const radius = 2.4 + Math.pow(Math.random(), 1.4) * 9;
      const pos = randomOnSphere(radius);
      pos.y *= 0.8;
      return {
        pos,
        color: pickColor(Math.random() * 0.45),
        size: 0.35 + Math.random() * 1.0,
      };
    });
    const cloudMat = makeMaterial(1, pixelRatio);
    const cloud = new THREE.Points(cloudGeo, cloudMat);
    root.add(cloud);

    /* 4. Orbital rings: flattened particle discs at different tilts */
    const ringGroup = new THREE.Group();
    const ringTilts = [
      [0.35, 0.0, 0.2],
      [-0.9, 0.4, 0.0],
      [1.2, -0.3, 0.6],
    ];
    const perRing = Math.floor(RING_COUNT / ringTilts.length);
    ringTilts.forEach(([rx, ry, rz], idx) => {
      const geo = buildGeometry(perRing, () => {
        const a = Math.random() * Math.PI * 2;
        const r = 2.6 + idx * 0.65 + (Math.random() - 0.5) * 0.35;
        return {
          pos: new THREE.Vector3(
            Math.cos(a) * r,
            (Math.random() - 0.5) * 0.12,
            Math.sin(a) * r
          ),
          color: pickColor(0.35 + Math.random() * 0.5),
          size: 0.5 + Math.random() * 0.9,
        };
      });
      const mat = makeMaterial(1, pixelRatio);
      const pts = new THREE.Points(geo, mat);
      pts.rotation.set(rx, ry, rz);
      pts.userData.speed = (idx % 2 === 0 ? 1 : -1) * (0.08 + idx * 0.035);
      ringGroup.add(pts);
    });
    root.add(ringGroup);

    /* 5. Streams: energy streaks spiralling out from the core */
    const streamGeo = buildGeometry(STREAM_COUNT, () => {
      const arm = Math.floor(Math.random() * 5);
      const t = Math.pow(Math.random(), 0.8);
      const r = 1.8 + t * 6.5;
      const a = (arm / 5) * Math.PI * 2 + t * 5.0 + (Math.random() - 0.5) * 0.25;
      return {
        pos: new THREE.Vector3(
          Math.cos(a) * r,
          (Math.random() - 0.5) * (0.4 + t * 1.6),
          Math.sin(a) * r
        ),
        color: pickColor(0.55 - t * 0.45 + Math.random() * 0.2),
        size: 0.45 + Math.random() * 0.9,
      };
    });
    const streamMat = makeMaterial(1, pixelRatio);
    const stream = new THREE.Points(streamGeo, streamMat);
    root.add(stream);

    const materials = [coreMat, haloMat, cloudMat, streamMat];
    ringGroup.children.forEach((c) => materials.push(c.material));

    /* Interaction */
    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    const onMove = (e) => {
      const x = e.touches ? e.touches[0].clientX : e.clientX;
      const y = e.touches ? e.touches[0].clientY : e.clientY;
      mouse.tx = (x / window.innerWidth) * 2 - 1;
      mouse.ty = (y / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("touchmove", onMove, { passive: true });

    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.position.z = window.innerWidth < 768 ? 12 : 9.5;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    /* Loop */
    const clock = new THREE.Clock();
    let raf = 0;

    const animate = () => {
      raf = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      // heartbeat-like pulse
      const pulse =
        Math.pow(Math.max(0, Math.sin(t * 1.4)), 6) * 0.8 +
        0.2 * Math.sin(t * 0.7);

      materials.forEach((m) => {
        m.uniforms.uTime.value = t;
        m.uniforms.uPulse.value = pulse;
      });

      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;

      core.rotation.y = t * 0.12;
      core.rotation.x = Math.sin(t * 0.2) * 0.15;
      halo.rotation.y = -t * 0.06;
      cloud.rotation.y = t * 0.025;
      cloud.rotation.x = Math.sin(t * 0.05) * 0.1;
      stream.rotation.y = t * 0.07;
      ringGroup.children.forEach((r) => {
        r.rotation.y += r.userData.speed * 0.016;
      });

      root.rotation.y = mouse.x * 0.35;
      root.rotation.x = mouse.y * 0.2;

      const s = 1 + pulse * 0.025;
      root.scale.setScalar(s);

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("resize", onResize);
      root.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) o.material.dispose();
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
    />
  );
}
