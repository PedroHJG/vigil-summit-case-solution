import React, { useEffect, useRef } from "react";
// Ícones Material (Event / LocationOn) inline: mesmos paths do @mui/icons-material,
// sem carregar @mui + @emotion no bundle por causa de 2 ícones.
const EventIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z" />
  </svg>
);
const LocationOnIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
  </svg>
);
import { scrollToTarget } from "../../utils/scrollTo";
import { gsap } from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
import ParticleBackground from "./particles/ParticleBackground";

gsap.registerPlugin(TextPlugin);

export default function HeroSection() {
  const titleRef = useRef<HTMLSpanElement>(null);
  const cursorRef = useRef<HTMLSpanElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Animação do cursor piscando (pipe roxo)
    gsap.to(cursorRef.current, {
      opacity: 0,
      repeat: 2,
      yoyo: true,
      duration: 0.3,
      onComplete: () => {
        gsap.to(cursorRef.current, {
          opacity: 0,
          duration: 0.5,
          onComplete: () => {
            gsap.set(cursorRef.current, { display: "none" });
          },
        });
      },
    });

    const tl = gsap.timeline();

    // Efeito de digitação no H1
    tl.to(titleRef.current, {
      duration: 1,
      text: "Vigil Summit <span class=\"text-[#8d2fc3] italic font-['ZT_Nature']\">2026</span>",
      ease: "none",
    })
      // Faz o fade in e o movimento de baixo para cima nos outros elementos
      .fromTo(
        ".animate-up",
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 0.8, stagger: 0.15, ease: "power3.out" },
        "+=0.2",
      );
  }, []);

  return (
    <section
      id="inicio"
      className="w-full bg-white flex flex-col items-center pt-10  relative min-h-screen"
    >
      {/* Background de Partículas Interativo (Three.js) */}
      <ParticleBackground />

      {/* Top Text Content */}
      <div
        ref={contentRef}
        className="max-w-4xl mx-auto px-6 text-center space-y-6 relative z-10 pointer-events-auto flex flex-col items-center justify-center pt-16"
      >
        <h1 className="font-['ZT_Nature'] text-6xl md:text-7xl lg:text-8xl font-thin leading-tight text-[#181818] min-h-[1.2em]">
          <span ref={titleRef}></span>
          <span ref={cursorRef} className="text-[#8d2fc3] font-light">
            |
          </span>
        </h1>

        <p className="animate-up opacity-0 font-['Inter'] font-light text-sm md:text-base text-gray-400 max-w-2xl mx-auto italic">
          Ameaças evoluem em tempo real. A sua postura de segurança também deve
          evoluir.
        </p>

        <p className="animate-up opacity-0 font-['Inter'] font-light text-lg md:text-xl text-[#181818] max-w-3xl mx-auto pt-4 leading-relaxed">
          Junte-se a um grupo seleto de{" "}
          <span className="font-semibold">120 líderes de tecnologia</span> para
          descobrir como a Inteligência Artificial está redefinindo o{" "}
          <span className="font-semibold">monitoramento contínuo</span>, a{" "}
          <span className="font-semibold">gestão de vulnerabilidades</span> e a{" "}
          <span className="font-semibold">
            conformidade (ISO 27001, LGPD e SOC 2)
          </span>
          .
        </p>

        <div className="flex flex-row items-center justify-center gap-4 md:gap-8 pt-6 pb-6 text-[#181818]">
          <div className="animate-up opacity-0 flex items-center space-x-2">
            <EventIcon className="w-5 h-5" />
            <span className="font-medium text-sm md:text-base">20/08/2026</span>
          </div>
          <div className="animate-up opacity-0 flex items-center space-x-2">
            <LocationOnIcon className="w-5 h-5" />
            <span className="font-medium text-sm md:text-base">
              Hotel Hyatt, São Paulo
            </span>
          </div>
        </div>

        <button
          onClick={() => scrollToTarget("#inscricao")}
          className="animate-up opacity-0 bg-[#484848] text-white px-8 py-4 rounded-lg font-['Inter'] font-medium text-sm hover:bg-[#383838] transition-colors shadow-lg cursor-pointer relative z-20"
        >
          Solicitar Minha Vaga Exclusiva
        </button>
      </div>
    </section>
  );
}
