import * as THREE from 'three';

/**
 * UniformManager
 * Mantém o dicionário de variáveis enviadas à GPU (Shader).
 * Nenhuma classe cria cópias dessas variáveis; elas são acessadas via referência.
 */
export class UniformManager {
    public uniforms: { [uniform: string]: THREE.IUniform };

    constructor() {
        this.uniforms = {
            uTime: { value: 0 },
            uMouse: { value: new THREE.Vector3(9999, 9999, 9999) },
            uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
            uPixelRatio: { value: window.devicePixelRatio },
            uNoiseStrength: { value: 0.4 },
            uInteractionRadius: { value: 180 }
        };
    }
}
