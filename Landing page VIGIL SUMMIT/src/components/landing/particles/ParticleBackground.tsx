import React, { useEffect, useRef, useState } from 'react';
import { MainParticlesScene } from './MainParticlesScene';

export default function ParticleBackground() {
    const containerRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        if (!canvasRef.current || !containerRef.current) return;

        const width = containerRef.current.clientWidth || window.innerWidth;
        const height = containerRef.current.clientHeight || window.innerHeight;

        const scene = new MainParticlesScene(canvasRef.current, width, height);
        
        scene.init();
        scene.resume();

        const resizeObserver = new ResizeObserver(() => {
            if (!containerRef.current) return;
            const newWidth = containerRef.current.clientWidth;
            const newHeight = containerRef.current.clientHeight;
            
            scene.resize(newWidth, newHeight);
        });
        
        resizeObserver.observe(containerRef.current);

        // Observer para verificar se a Hero está na tela e executar fade-in/fade-out
        const io = new IntersectionObserver(([entry]) => {
            setIsVisible(entry.isIntersecting);
            if (entry.isIntersecting) {
                scene.resume();
            } else {
                // Delay para esperar a transição de fade CSS terminar antes de pausar o renderizador
                setTimeout(() => scene.pause(), 1000); 
            }
        }, { threshold: 0.1 });
        
        io.observe(containerRef.current);

        return () => {
            resizeObserver.disconnect();
            io.disconnect();
            scene.dispose();
        };
    }, []);

    return (
        <div 
          ref={containerRef} 
          className={`absolute inset-0 w-full h-full z-0 pointer-events-none overflow-hidden transition-opacity duration-1000 ease-in-out ${isVisible ? 'opacity-100' : 'opacity-0'}`}
        >
            <canvas ref={canvasRef} className="w-full h-full block" />
        </div>
    );
}
