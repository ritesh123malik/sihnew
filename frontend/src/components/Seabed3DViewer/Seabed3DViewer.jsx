import React, { useRef, useEffect, useState, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default function Seabed3DViewer({
  data = null,
  settings = {},
  onReady = null,
  onSelect = null,
  altitude = 15.0,
  depth = 25.0
}) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [selectedObject, setSelectedObject] = useState(null);
  const [hoveredObject, setHoveredObject] = useState(null);

  // Default configuration
  const defaultSettings = {
    colorScheme: 'elevation', // 'elevation', 'intensity', 'depth'
    showWater: true,
    showShadows: true,
    showTargets: true,
    showGrid: true,
    elevationScale: 4.0, // Vertical exaggeration
    pointSize: 3,
    wireframe: false,
    fogEnabled: true,
    fogDensity: 0.0015
  };

  const config = { ...defaultSettings, ...settings };

  // Process data from API or create synthetic bathymetry from altitude/depth
  const processedData = useMemo(() => {
    if (data && (data.point_cloud || data.elevation_grid)) {
      return {
        pointCloud: data.point_cloud || [],
        elevationGrid: data.elevation_grid || null,
        shadows: data.shadows || [],
        metadata: data.metadata || {}
      };
    }

    // Default synthetic seabed if no backend grid passed
    const synthPoints = [];
    const rows = 40;
    const cols = 40;
    const spacing = 2.0;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = (c - cols / 2) * spacing;
        const y = (r - rows / 2) * spacing;
        const dist = Math.hypot(x, y);

        let z = Math.sin(r * 0.25) * Math.cos(c * 0.25) * 1.5;
        // Central target mound
        if (dist < 8) {
          z += (8 - dist) * 0.8;
        }

        synthPoints.push({
          x: x,
          y: y,
          z: z,
          intensity: 0.4 + (z + 2) / 6
        });
      }
    }

    const synthShadows = [
      {
        bbox: [15, 15, 25, 25],
        centroid: [0, 0],
        length_m: 8.5,
        estimated_height: 3.2,
        target_centroid: [0, -2],
        type: 'Active Ghost Net / Debris'
      }
    ];

    return {
      pointCloud: synthPoints,
      elevationGrid: null,
      shadows: synthShadows,
      metadata: { H_s: altitude, R_s: depth * 2 }
    };
  }, [data, altitude, depth]);

  // Three.js Scene Setup & Render Loop
  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth || 640;
    const height = containerRef.current.clientHeight || 420;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060f1e); // Tactical marine navy

    if (config.fogEnabled) {
      scene.fog = new THREE.FogExp2(0x060f1e, config.fogDensity);
    }

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 2000);
    camera.position.set(0, 45, 75);

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: true
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;

    // 4. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2.05; // Prevent flipping under seafloor
    controls.minDistance = 10;
    controls.maxDistance = 300;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0x224466, 1.2);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x38bdf8, 2.0);
    dirLight.position.set(40, 80, 50);
    scene.add(dirLight);

    const bottomLight = new THREE.DirectionalLight(0x0284c7, 0.8);
    bottomLight.position.set(-40, -40, -50);
    scene.add(bottomLight);

    // 6. Bathymetry Point Cloud
    const { pointCloud, shadows } = processedData;

    if (pointCloud && pointCloud.length > 0) {
      const geometry = new THREE.BufferGeometry();
      const positions = [];
      const colors = [];

      const elevations = pointCloud.map((p) => p.z);
      const minElev = Math.min(...elevations);
      const maxElev = Math.max(...elevations);
      const elevRange = maxElev - minElev || 1.0;

      pointCloud.forEach((pt) => {
        positions.push(pt.x, pt.z * config.elevationScale, -pt.y);

        let color = new THREE.Color();
        if (config.colorScheme === 'elevation') {
          const norm = (pt.z - minElev) / elevRange;
          // Gradient: Deep Blue -> Cyan -> Yellow -> Red
          color.setHSL(0.65 - norm * 0.65, 0.9, 0.55);
        } else if (config.colorScheme === 'intensity') {
          color.setRGB(pt.intensity, pt.intensity, pt.intensity);
        } else {
          color.setHex(0x00f0ff);
        }

        colors.push(color.r, color.g, color.b);
      });

      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

      const pointsMaterial = new THREE.PointsMaterial({
        size: config.pointSize,
        vertexColors: true,
        transparent: true,
        opacity: 0.85,
        sizeAttenuation: true
      });

      const pointsMesh = new THREE.Points(geometry, pointsMaterial);
      pointsMesh.name = 'bathymetry_points';
      scene.add(pointsMesh);
    }

    // 7. Render Acoustic Shadows & Target Beacons
    if (config.showShadows && shadows && shadows.length > 0) {
      shadows.forEach((shadow, idx) => {
        const estHeight = shadow.estimated_height || 2.5;
        const targetPos = shadow.target_centroid || [0, 0];

        // Target Sphere
        if (config.showTargets) {
          const sphereGeo = new THREE.SphereGeometry(estHeight * 0.6, 16, 16);
          const sphereMat = new THREE.MeshPhongMaterial({
            color: 0xef4444,
            emissive: 0x7f1d1d,
            shininess: 90
          });
          const targetSphere = new THREE.Mesh(sphereGeo, sphereMat);
          targetSphere.position.set(
            targetPos[0],
            estHeight * config.elevationScale,
            -targetPos[1]
          );
          targetSphere.name = `target_${idx}`;
          targetSphere.userData = {
            type: shadow.type || 'Acoustic Hazard Target',
            height: estHeight,
            shadowLength: shadow.length_m || 8.0,
            ...shadow
          };
          scene.add(targetSphere);
        }

        // Acoustic Shadow Plane on Seafloor
        const shadowPlaneGeo = new THREE.PlaneGeometry(
          Math.max(4, (shadow.length_m || 6) * 0.8),
          Math.max(3, estHeight * 1.5)
        );
        const shadowMat = new THREE.MeshBasicMaterial({
          color: 0x000000,
          transparent: true,
          opacity: 0.6,
          side: THREE.DoubleSide
        });
        const shadowPlane = new THREE.Mesh(shadowPlaneGeo, shadowMat);
        shadowPlane.rotation.x = -Math.PI / 2;
        shadowPlane.position.set(
          targetPos[0],
          -0.1,
          -(targetPos[1] + (shadow.length_m || 6) * 0.4)
        );
        scene.add(shadowPlane);
      });
    }

    // 8. Grid Helper
    if (config.showGrid) {
      const grid = new THREE.GridHelper(120, 24, 0x0284c7, 0x1e293b);
      grid.position.y = -0.2;
      scene.add(grid);
    }

    // 9. Animation Loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 10. Resize Observer
    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    if (onReady) onReady(scene);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
      controls.dispose();
      renderer.dispose();
    };
  }, [processedData, config, onReady]);

  // Raycasting for target click selection
  const handleCanvasClick = (e) => {
    if (!canvasRef.current || !onSelect) return;
    // Callback if target selected
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '380px',
        background: '#060f1e',
        borderRadius: '8px',
        overflow: 'hidden'
      }}
    >
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        style={{ width: '100%', height: '100%', display: 'block', cursor: 'grab' }}
      />

      {/* Header Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          left: 14,
          background: 'rgba(10, 25, 47, 0.85)',
          padding: '8px 14px',
          borderRadius: '6px',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          color: '#e2e8f0',
          fontSize: '12px',
          fontFamily: 'monospace',
          backdropFilter: 'blur(4px)',
          zIndex: 10
        }}
      >
        <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: '3px' }}>
          🌊 3D ACOUSTIC SHADOW BATHYMETRY
        </div>
        <div style={{ color: '#94a3b8', fontSize: '11px' }}>
          Equation: h = (L_s × H_s) / R_s · {processedData.pointCloud.length} soundings
        </div>
      </div>

      {/* Controls Overlay Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          right: 14,
          background: 'rgba(10, 25, 47, 0.85)',
          padding: '8px 12px',
          borderRadius: '6px',
          border: '1px solid rgba(100, 116, 139, 0.3)',
          color: '#94a3b8',
          fontSize: '10px',
          fontFamily: 'monospace',
          backdropFilter: 'blur(4px)',
          zIndex: 10
        }}
      >
        <div>Left Drag: <strong>Rotate 3D View</strong></div>
        <div>Right Drag: <strong>Pan Scene</strong></div>
        <div>Scroll: <strong>Zoom Elevation</strong></div>
      </div>
    </div>
  );
}
