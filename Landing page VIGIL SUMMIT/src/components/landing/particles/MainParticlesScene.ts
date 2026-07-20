import * as THREE from 'three';
import { Camera } from './Camera';
import { Renderer } from './Renderer';
import { UniformManager } from './UniformManager';
import { MouseController } from './MouseController';
import { RaycasterController } from './RaycasterController';
import { ParticleSystem } from './ParticleSystem';
import { AnimationLoop } from './AnimationLoop';

/**
 * MainParticlesScene
 * Fachada principal. Nenhuma matemática vetorial profunda acontece aqui,
 * apenas a coordenação limpa dos módulos em preRender -> render -> postRender.
 */
export class MainParticlesScene {
    private renderer!: Renderer;
    private scene!: THREE.Scene;
    private camera!: Camera;
    private raycaster!: RaycasterController;
    private particles!: ParticleSystem;
    private clock!: THREE.Clock;
    private uniformsManager!: UniformManager;
    private mouseController!: MouseController;
    private animationLoop!: AnimationLoop;

    private loaded: boolean = false;
    private isPaused: boolean = false;

    private targetCloudPos: THREE.Vector3 = new THREE.Vector3();
    private ghostCloudPos: THREE.Vector3 = new THREE.Vector3();
    private currentCloudPos: THREE.Vector3 = new THREE.Vector3();

    constructor(private canvas: HTMLCanvasElement, private width: number, private height: number) {}

    public init() {
        this.scene = new THREE.Scene();
        this.clock = new THREE.Clock();
        
        this.camera = new Camera(this.width, this.height);
        this.renderer = new Renderer(this.canvas, this.width, this.height);
        
        this.uniformsManager = new UniformManager();
        this.mouseController = new MouseController();
        this.raycaster = new RaycasterController();
        
        this.scene.add(this.raycaster.getPlane());

        this.particles = new ParticleSystem(400, this.uniformsManager.uniforms);
        this.scene.add(this.particles.mesh);

        this.animationLoop = new AnimationLoop(() => this.render());

        this.loaded = true;
    }

    public render() {
        if (!this.loaded) return;
        if (this.isPaused) return;

        const delta = this.clock.getDelta();
        this.preRender(delta);

        this.renderer.instance.setRenderTarget(null);
        this.renderer.instance.autoClear = false;
        this.renderer.instance.clear();

        this.renderer.instance.render(this.scene, this.camera.instance);

        this.postRender();
    }

    private preRender(delta: number) {
        this.uniformsManager.uniforms.uTime.value = this.clock.getElapsedTime();
        
        if (this.mouseController.isActive) {
            this.raycaster.intersect(
                this.mouseController.ndc, 
                this.camera.instance, 
                this.targetCloudPos // Posição alvo = local do mouse
            );
        } else {
            this.targetCloudPos.set(0, 0, 0);
        }

        // Tática do Lerp Duplo: O ghost persegue o mouse num ritmo linear, 
        // e a nuvem verdadeira persegue o ghost. Como a distância para o ghost começa pequena
        // e vai aumentando, a velocidade da nuvem começa em ZERO e ACELERA, dando 100% de feel "ease-in"
        const safeDelta = Math.min(delta, 0.032);
        
        // Ghost segue agressivo, mas não instantâneo
        this.ghostCloudPos.lerp(this.targetCloudPos, 6.0 * safeDelta);
        
        // Nuvem persegue o ghost, gerando o delay e arrancada curva de aceleração de "lento para rápido"
        this.currentCloudPos.lerp(this.ghostCloudPos, 3.5 * safeDelta);

        this.particles.mesh.position.copy(this.currentCloudPos);

        // Repassa para a GPU a posição do mouse "relativa" à nuvem
        this.uniformsManager.uniforms.uMouse.value.copy(this.targetCloudPos).sub(this.currentCloudPos);
    }

    private postRender() {
        // Hooks de pós-processamento, caso necessários
    }

    public resize(width: number, height: number) {
        this.width = width;
        this.height = height;
        this.camera.resize(width, height);
        this.renderer.resize(width, height);
        this.uniformsManager.uniforms.uResolution.value.set(width, height);
    }

    public pause() {
        this.isPaused = true;
        this.animationLoop.stop();
    }

    public resume() {
        this.isPaused = false;
        this.clock.start();
        this.animationLoop.start();
    }

    public dispose() {
        this.animationLoop.stop();
        this.mouseController.dispose();
        this.particles.dispose();
        this.renderer.instance.dispose();
    }
}
