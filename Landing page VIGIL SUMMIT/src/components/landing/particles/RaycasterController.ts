import * as THREE from 'three';

/**
 * RaycasterController
 * Transforma o NDC 2D em um ponto no mundo 3D no plano Z=0.
 */
export class RaycasterController {
    private raycaster: THREE.Raycaster;
    private interactionPlane: THREE.Mesh;

    constructor() {
        this.raycaster = new THREE.Raycaster();
        
        // Plano de colisão invisível na profundidade Z=0
        const geometry = new THREE.PlaneGeometry(10000, 10000);
        const material = new THREE.MeshBasicMaterial({ visible: false });
        this.interactionPlane = new THREE.Mesh(geometry, material);
    }

    public getPlane() {
        return this.interactionPlane;
    }

    public intersect(ndc: THREE.Vector2, camera: THREE.PerspectiveCamera, targetVec: THREE.Vector3) {
        this.raycaster.setFromCamera(ndc, camera);
        
        const hit = this.raycaster.intersectObject(this.interactionPlane);
        
        if (hit.length > 0) {
            targetVec.copy(hit[0].point); // Sem instanciar novo Vector3
        } else {
            targetVec.set(9999, 9999, 9999);
        }
    }
}
