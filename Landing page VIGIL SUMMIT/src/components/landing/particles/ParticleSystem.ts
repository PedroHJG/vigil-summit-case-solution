import * as THREE from 'three';
import { vertexShader } from './shaders/particle.vert';
import { fragmentShader } from './shaders/particle.frag';

/**
 * ParticleSystem
 * Aloca a geometria, atributos (pos, size, random) em Float32Array e constrói o ShaderMaterial.
 * Zero CPU updates após o init. A GPU toma controle 100%.
 */
export class ParticleSystem {
    public mesh: THREE.Points;
    public geometry: THREE.BufferGeometry;
    public material: THREE.ShaderMaterial;

    constructor(count: number, uniforms: any) {
        this.geometry = new THREE.BufferGeometry();
        
        const positions = new Float32Array(count * 3);
        const sizes = new Float32Array(count);
        const random = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            
            // Cria um cluster orgânico concentrado (distribuição circular suave)
            // Math.random() * Math.random() aglomera mais pontos no centro e espalha nas bordas
            const radius = Math.random() * Math.random() * 1500; 
            const angle = Math.random() * Math.PI * 2;
            
            positions[i3] = Math.cos(angle) * radius;
            positions[i3 + 1] = Math.sin(angle) * radius;
            positions[i3 + 2] = (Math.random() - 0.5) * 80; // Profundidade Z

            // Atributos base 
            sizes[i] = Math.random() * .5 + 1.2;
            random[i] = Math.random() * 100;
        }

        this.geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        this.geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));
        this.geometry.setAttribute('random', new THREE.Float32BufferAttribute(random, 1));

        this.material = new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            blending: THREE.NormalBlending,
            uniforms,
            vertexShader,
            fragmentShader
        });

        this.mesh = new THREE.Points(this.geometry, this.material);
    }

    public dispose() {
        this.geometry.dispose();
        this.material.dispose();
    }
}
