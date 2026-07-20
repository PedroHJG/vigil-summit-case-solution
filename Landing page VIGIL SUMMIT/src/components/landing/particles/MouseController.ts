import * as THREE from 'three';

/**
 * MouseController
 * Responsabilidade: Escutar eventos de DOM e normalizar coordenadas (NDC) sem lógica 3D pesada.
 */
export class MouseController {
    public ndc: THREE.Vector2;
    public isActive: boolean;

    constructor() {
        this.ndc = new THREE.Vector2(9999, 9999);
        this.isActive = false;

        this.onMouseMove = this.onMouseMove.bind(this);
        this.onMouseLeave = this.onMouseLeave.bind(this);

        window.addEventListener('mousemove', this.onMouseMove);
        window.addEventListener('mouseleave', this.onMouseLeave);
        window.addEventListener('blur', this.onMouseLeave);
    }

    private onMouseMove(event: MouseEvent) {
        this.isActive = true;
        this.ndc.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.ndc.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    private onMouseLeave() {
        this.isActive = false;
        // Joga para longe
        this.ndc.set(9999, 9999);
    }

    public dispose() {
        window.removeEventListener('mousemove', this.onMouseMove);
        window.removeEventListener('mouseleave', this.onMouseLeave);
        window.removeEventListener('blur', this.onMouseLeave);
    }
}
