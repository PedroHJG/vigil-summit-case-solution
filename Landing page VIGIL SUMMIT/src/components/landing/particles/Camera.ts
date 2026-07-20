import * as THREE from 'three';

export class Camera {
    public instance: THREE.PerspectiveCamera;
    private width: number;
    private height: number;

    constructor(width: number, height: number) {
        this.width = width;
        this.height = height;
        this.instance = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        // Posicionada adequadamente para ter um bom campo de visão 2D no plano Z=0
        this.instance.position.z = 250;
    }

    public resize(width: number, height: number) {
        this.width = width;
        this.height = height;
        this.instance.aspect = width / height;
        this.instance.updateProjectionMatrix();
    }
}
