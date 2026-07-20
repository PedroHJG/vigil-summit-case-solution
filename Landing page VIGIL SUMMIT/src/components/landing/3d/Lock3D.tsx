import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import gsap from 'gsap';

// Padrão Vite-safe para importação de arquivos que não são nativamente suportados como imagens
// O .glb foi comprimido com Draco (55,9 MB -> 1,4 MB); o decoder vive em /public/draco.
const lockModelUrl = new URL('../../../assets/3d/lock3d.glb', import.meta.url).href;

export default function Lock3D() {
    const containerRef = useRef<HTMLDivElement>(null);
    const mountRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current || !mountRef.current) return;
        const mountEl = mountRef.current;

        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;

        const scene = new THREE.Scene();

        // Câmera mais afastada (Z=12) garante que o modelo tenha espaço de respiro (padding)
        // para girar livremente sem que o WebGL corte as extremidades (overflow)
        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
        camera.position.set(0, 0, 12);

        const renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: false, // Antialias desativado para ganho massivo de FPS
            powerPreference: 'high-performance', // Exige a GPU dedicada
        });
        renderer.setSize(width, height);
        // Trava a densidade de pixels em 1 para não calcular o quádruplo de pixels em telas Retina/4K
        renderer.setPixelRatio(1);
        mountEl.appendChild(renderer.domElement);

        // Luzes estáticas: trava as matrizes (matrixAutoUpdate=false) — nada é
        // recalculado por frame para elas.
        const ambientLight = new THREE.AmbientLight(0xffffff, 5.5);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 3);
        directionalLight.position.set(5, -15, 7);
        directionalLight.updateMatrix();
        directionalLight.matrixAutoUpdate = false;
        scene.add(directionalLight);

        const pointLight = new THREE.PointLight(0x8d2fc3, 500, 200);
        pointLight.position.set(-3, -3, 3);
        pointLight.updateMatrix();
        pointLight.matrixAutoUpdate = false;
        scene.add(pointLight);

        let model: THREE.Group | null = null;
        const targetRotation = { x: 0, y: 0 };
        const currentRotation = { x: 0, y: 0 };

        const finalX = 0.8;
        const baseRotationY = Math.PI / 2;

        const wrapperGroup = new THREE.Group();
        wrapperGroup.position.x = finalX;
        scene.add(wrapperGroup);

        // Loader com Draco: a geometria comprimida é decodificada em WASM
        // (Web Worker interno do DRACOLoader), fora da thread principal.
        const dracoLoader = new DRACOLoader();
        dracoLoader.setDecoderPath('/draco/');
        const loader = new GLTFLoader();
        loader.setDRACOLoader(dracoLoader);

        // Repulsão baseada na tela toda!
        const onMouseMove = (event: MouseEvent) => {
            if (!isVisible || !model) return; // ignora fora da tela / antes do load
            const x = (event.clientX / window.innerWidth) * 2 - 1;
            const y = -(event.clientY / window.innerHeight) * 2 + 1;

            targetRotation.y = x * Math.PI * 0.25;
            targetRotation.x = -y * Math.PI * 0.25;
        };

        const onMouseLeave = () => {
            if (!isVisible) return;
            targetRotation.x = 0;
            targetRotation.y = 0;
        };

        window.addEventListener('mousemove', onMouseMove, { passive: true });
        window.addEventListener('mouseleave', onMouseLeave);

        // autoAlpha = opacity + visibility: quando 0, o elemento sai do fluxo de
        // pintura do navegador (em vez de pintar um layer transparente).
        gsap.set(mountEl, { x: 1500, autoAlpha: 0 });
        const tweens: gsap.core.Tween[] = [];

        // Offset Y para mover o cadeado mais para baixo permanentemente
        const yOffset = -0.8;

        // ==== Loop de render controlado por visibilidade ====
        // Em vez de "early return" dentro do rAF (que continua acordando a CPU a
        // cada frame), o loop é parado/retomado por completo pelo observer.
        let animationFrameId = 0;
        let isVisible = false;
        let isLoaded = false;

        const animate = () => {
            animationFrameId = requestAnimationFrame(animate);

            if (model) {
                currentRotation.x += (targetRotation.x - currentRotation.x) * 0.1;
                currentRotation.y += (targetRotation.y - currentRotation.y) * 0.1;

                model.rotation.x = currentRotation.x;
                model.rotation.y = currentRotation.y + baseRotationY;

                // Aplica a onda de flutuação sobre a posição rebaixada
                wrapperGroup.position.y = yOffset + Math.sin(Date.now() * 0.0015) * 0.15;
            }

            renderer.render(scene, camera);
        };

        const startLoop = () => {
            if (!animationFrameId) animate();
        };
        const stopLoop = () => {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = 0;
            }
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                isVisible = entry.isIntersecting;
                if (isVisible) startLoop();
                else stopLoop(); // zero trabalho de CPU/GPU fora da tela

                if (isVisible && !isLoaded) {
                    isLoaded = true; // Impede que carregue várias vezes

                    // LAZY LOAD: o arquivo só é buscado quando a seção aparece
                    loader.load(lockModelUrl, (gltf) => {
                        model = gltf.scene;

                        // Modifica os materiais para deixar tudo Roxo metálico
                        model.traverse((child) => {
                            if ((child as THREE.Mesh).isMesh) {
                                const mesh = child as THREE.Mesh;
                                // frustumCulled já é true por padrão no Three —
                                // a malha some do pipeline ao sair do campo de visão.
                                const material = mesh.material as THREE.MeshStandardMaterial;
                                if (material) {
                                    material.color.setHex(0xb341f2);
                                    material.metalness = 0.7;
                                    material.roughness = 0.2;
                                }
                            }
                        });

                        const box = new THREE.Box3().setFromObject(model);
                        const center = box.getCenter(new THREE.Vector3());
                        model.position.sub(center);

                        const size = box.getSize(new THREE.Vector3()).length();
                        const targetScale = 9.5 / size; // compensa o recuo da câmera
                        model.scale.setScalar(targetScale);

                        wrapperGroup.add(model);

                        // Pré-compila os shaders fora do caminho crítico: evita o
                        // "hitch" do primeiro frame em que o modelo aparece.
                        renderer.compile(scene, camera);

                        // O decoder Draco (WASM/worker) não é mais necessário
                        dracoLoader.dispose();

                        // Dispara a animação APENAS após o modelo estar 100% carregado
                        tweens.push(
                            gsap.to(mountEl, {
                                x: 0,
                                autoAlpha: 1,
                                duration: 2.6,
                                ease: 'power3.inOut',
                            }),
                            gsap.fromTo(
                                wrapperGroup.rotation,
                                { y: Math.PI * 1.5 },
                                { y: 0, duration: 2.6, ease: 'power3.inOut' }
                            )
                        );
                    });
                }
            });
        }, { threshold: 0.05 });

        observer.observe(containerRef.current);

        const handleResize = () => {
            if (!containerRef.current) return;
            const newWidth = containerRef.current.clientWidth;
            const newHeight = containerRef.current.clientHeight;
            camera.aspect = newWidth / newHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(newWidth, newHeight);
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseleave', onMouseLeave);
            observer.disconnect();
            stopLoop();

            // GSAP: mata tweens pendentes (evita callbacks órfãos e vazamento)
            tweens.forEach((t) => t.kill());
            gsap.killTweensOf(mountEl);

            // Three.js não libera GPU sozinho: dispose de geometrias, materiais
            // e texturas de toda a cena antes de derrubar o renderer.
            scene.traverse((obj) => {
                const mesh = obj as THREE.Mesh;
                if (mesh.isMesh) {
                    mesh.geometry?.dispose();
                    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                    materials.forEach((mat) => {
                        Object.values(mat).forEach((v) => {
                            if (v instanceof THREE.Texture) v.dispose();
                        });
                        mat.dispose();
                    });
                }
            });
            dracoLoader.dispose();
            renderer.dispose();
            if (mountEl.contains(renderer.domElement)) {
                mountEl.removeChild(renderer.domElement);
            }
        };
    }, []);

    return (
        <div ref={containerRef} className="w-full h-full relative z-30 pointer-events-auto" style={{ minHeight: '400px' }}>
            <div ref={mountRef} className="w-full h-full absolute inset-0" />
        </div>
    );
}