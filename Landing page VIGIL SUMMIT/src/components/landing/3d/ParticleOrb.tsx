import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function ParticleOrb() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const width = mount.clientWidth
    const height = mount.clientHeight

    // Renderer (Otimizado com high-performance e pixelRatio travado)
    const renderer = new THREE.WebGLRenderer({ 
      antialias: false, 
      alpha: true,
      powerPreference: "high-performance"
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
    mount.appendChild(renderer.domElement)

    // Scene + Camera
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100)
    // Afasta a câmera para diminuir o tamanho geral do orbe na tela
    camera.position.z = 5.5

    // === GEOMETRIA DE PARTÍCULAS ===
    const COUNT = 5000
    const positions = new Float32Array(COUNT * 3)
    const sizes = new Float32Array(COUNT)
    const phi = Math.PI * (3 - Math.sqrt(5)) // golden angle

    for (let i = 0; i < COUNT; i++) {
      // Distribuição em esfera com perturbação orgânica
      const y = 1 - (i / (COUNT - 1)) * 2
      const radius = Math.sqrt(1 - y * y)
      const theta = phi * i

      const noise = 0.15 * Math.sin(theta * 3) * Math.cos(y * 4)
      const r = 1.0 + noise

      positions[i * 3] = Math.cos(theta) * radius * r
      positions[i * 3 + 1] = y * r
      positions[i * 3 + 2] = Math.sin(theta) * radius * r

      // Tamanho varia com posição (bordas menores)
      const dist = Math.sqrt(
        positions[i * 3] ** 2 +
        positions[i * 3 + 1] ** 2 +
        positions[i * 3 + 2] ** 2
      )
      sizes[i] = THREE.MathUtils.lerp(0.008, 0.02, 1 - (dist - 0.8) / 0.4)
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))

    // Shader para partículas circulares com tamanho variável
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color('#999999') }, // Mais cinza (claro)
        uMousePos: { value: new THREE.Vector3(9999, 9999, 9999) } // Posição 3D do mouse
      },
      vertexShader: `
        attribute float aSize;
        uniform float uTime;
        uniform vec3 uMousePos;
        varying float vAlpha;

        void main() {
          vec3 pos = position;

          // Deformação orgânica suavizada (movimento mais sutil)
          float wave1 = sin(pos.y * 4.0 + uTime * 1.2) * 0.08;
          float wave2 = cos(pos.x * 3.5 + uTime * 0.8) * 0.08;
          float wave3 = sin(pos.z * 5.0 + uTime * 1.5) * 0.05;
          pos += normalize(pos) * (wave1 + wave2 + wave3);

          // Efeito Magnético: Atração APENAS nas partículas próximas ao mouse
          float distToMouse = distance(pos, uMousePos);
          // O raio de influência agora é bem menor (0.7). Quanto mais perto, mais atrai.
          float pull = smoothstep(0.9, 0.0, distToMouse);
          pos += normalize(uMousePos - pos) * pull * 0.4;

          vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
          gl_Position = projectionMatrix * mvPos;

          // Tamanho em pixels
          gl_PointSize = aSize * (600.0 / -mvPos.z);

          // Sem opacidade de profundidade 3D extrema. 
          // Apenas suaviza as bordas externas do globo.
          float dist = length(position);
          vAlpha = smoothstep(1.4, 0.7, dist);
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        varying float vAlpha;

        void main() {
          // Partícula circular
          vec2 uv = gl_PointCoord - 0.5;
          float d = length(uv);
          if (d > 0.5) discard;

          // Suaviza um pouco menos para pontos mais marcados como na ref
          float alpha = smoothstep(0.5, 0.3, d) * vAlpha;
          gl_FragColor = vec4(uColor, alpha);
        }
      `,
      transparent: true,
      depthWrite: false,
    })

    const points = new THREE.Points(geometry, material)
    // Estica levemente a geometria na horizontal para torná-la mais larga
    points.scale.x = 1.5;
    scene.add(points)

    // === INTERAÇÃO COM MOUSE ===
    const mouse = new THREE.Vector2(9999, 9999)
    const targetRotation = { x: 0, y: 0 }
    const raycaster = new THREE.Raycaster()
    const mousePlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)
    const intersectPoint = new THREE.Vector3()

    const onMouseMove = (e: MouseEvent) => {
      if (!isVisible) return // fora da tela: nem atualiza os alvos
      // Coordenadas normalizadas pro Raycaster
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1

      // Coordenadas pro giro (para manter a inércia do orbe)
      targetRotation.x += (mouse.y * 0.5 - targetRotation.x) * 0.05
      targetRotation.y += (mouse.x * 0.5 - targetRotation.y) * 0.05
    }
    window.addEventListener('mousemove', onMouseMove, { passive: true })

    // === LOOP DE ANIMAÇÃO ===
    let animId = 0
    let isVisible = false
    const clock = new THREE.Clock()

    const animate = () => {
      animId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()

      material.uniforms.uTime.value = t

      // Raycast do mouse para 3D (atração magnética)
      if (mouse.x !== 9999) {
        raycaster.setFromCamera(mouse, camera)
        raycaster.ray.intersectPlane(mousePlane, intersectPoint)
        
        // Suaviza a transição da posição do mouse no shader
        material.uniforms.uMousePos.value.lerp(intersectPoint, 0.1)
      }

      // Rotação autônoma suave
      points.rotation.y = t * 0.12
      points.rotation.x = Math.sin(t * 0.2) * 0.1

      // Adiciona o giro inercial extra do mouse
      points.rotation.x += targetRotation.x * 0.02
      points.rotation.y += targetRotation.y * 0.02

      renderer.render(scene, camera)
    }

    // Loop parado/retomado por completo conforme a visibilidade (nada de rAF
    // acordando a CPU com o orbe fora da tela)
    const startLoop = () => {
      if (!animId) animate()
    }
    const stopLoop = () => {
      if (animId) {
        cancelAnimationFrame(animId)
        animId = 0
      }
    }

    const io = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting
      if (isVisible) startLoop()
      else stopLoop()
    }, { threshold: 0.05 })
    io.observe(mount)

    // === RESIZE ===
    const onResize = () => {
      const w = mount.clientWidth
      const h = mount.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      io.disconnect()
      stopLoop()
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', onResize)
      if (mount && renderer.domElement && mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement)
      }
      geometry.dispose()
      material.dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <div ref={mountRef} className="w-full h-full min-h-[300px]"></div>
  )
}
