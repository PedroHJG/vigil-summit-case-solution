import React, { useRef } from 'react';
import ondaBG from '../../assets/images/wave.png';
import { useTypewriter } from '../../utils/animations';

export default function ProblemSection() {
  const containerRef = useRef<HTMLElement>(null);
  
  // Aplica o typewriter de forma modular e isolada apenas nos parágrafos dessa seção
  useTypewriter(containerRef, 'p');

  return (
    <section id="evento" ref={containerRef} className="relative py-24 px-6 bg-white text-[#181818]">
      {/* Decorative Wave Background on the left */}
      <div className="absolute top-[90%] md:top-[95%] -left-32 md:-left-64 w-[300px] md:w-[450px] lg:w-[600px] z-0 pointer-events-none rotate-30">
        <img src={ondaBG} alt="Ondas" className="w-full h-auto" />
      </div>

      <div className="max-w-4xl mx-auto space-y-12 relative z-10">
        <h2 className="font-['ZT_Nature'] font-thin text-5xl md:text-7xl leading-tight">
          <span className="text-[#b341f2]">O modelo</span> tradicional de<br />
          cibersegurança <span className="text-[#d93535] italic font-['ZT_Nature']">falhou.</span>
        </h2>
        
        <p className="font-['Inter'] font-light text-base md:text-xl text-gray-700 leading-relaxed">
          Auditorias anuais e varreduras periódicas <span className="font-semibold text-black">não são mais suficientes contra ataques cibernéticos impulsionados por IA.</span> Enquanto sua equipe analisa milhares de falsos positivos, riscos críticos e falhas de conformidade <span className="font-semibold text-black">passam despercebidas.</span>
        </p>

        <p className="font-['Inter'] font-light text-base md:text-xl text-gray-500 italic text-center py-4">
          É hora de mudar para a Defesa Ativa.
        </p>

        <p className="font-['Inter'] font-light text-base md:text-xl text-gray-700 leading-relaxed">
          No <span className="font-semibold text-black">Vigil Summit</span>, você verá na prática como <span className="font-semibold text-black">empresas líderes estão utilizando a plataforma SaaS da Vigil.AI para transformar dados caóticos em recomendações automatizadas de remediação.</span>
        </p>
      </div>
    </section>
  );
}
