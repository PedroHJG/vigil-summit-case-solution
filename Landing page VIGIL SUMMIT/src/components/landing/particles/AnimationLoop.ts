/**
 * AnimationLoop
 * Abstração pura para o requestAnimationFrame (Separation of Concerns).
 */
export class AnimationLoop {
    private animationFrame: number = 0;
    private renderCallback: () => void;

    constructor(renderCallback: () => void) {
        this.renderCallback = renderCallback;
        this.animate = this.animate.bind(this);
    }

    public start() {
        if (!this.animationFrame) {
            this.animate();
        }
    }

    public stop() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = 0;
        }
    }

    private animate() {
        this.animationFrame = requestAnimationFrame(this.animate);
        this.renderCallback();
    }
}
