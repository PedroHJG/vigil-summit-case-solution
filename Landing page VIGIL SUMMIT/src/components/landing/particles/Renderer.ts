import * as THREE from 'three';

export class Renderer {
    public instance: THREE.WebGLRenderer;

    constructor(canvas: HTMLCanvasElement, width: number, height: number) {
        this.instance = new THREE.WebGLRenderer({
            canvas,
            alpha: true, // Fundo transparente conforme requisitado
            antialias: true,
            powerPreference: "high-performance" // Melhor performance
        });
        
        // Evitar uso exagerado de recursos em monitores retina se não for necessário, máximo 2
        this.instance.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.instance.setSize(width, height);
    }

    public resize(width: number, height: number) {
        this.instance.setSize(width, height);
    }

    public render(scene: THREE.Scene, camera: THREE.Camera) {
        this.instance.render(scene, camera);
    }
}
