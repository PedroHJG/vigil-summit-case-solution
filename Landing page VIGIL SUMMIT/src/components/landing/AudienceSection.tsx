import React, { useRef } from 'react';
import bracoIA from '../../assets/images/bracoIA.png';
import ondaBG from '../../assets/images/wave.png';
import { useSlideIn } from '../../utils/animations';
import ParticleOrb from './3d/ParticleOrb';

export default function AudienceSection() {
  const containerRef = useRef<HTMLElement>(null);
  useSlideIn(containerRef, '.slide-target', 'left');

  return (
    <section ref={containerRef} className="relative py-12 lg:py-24 px-6 overflow-hidden min-h-[700px] flex items-center">
      {/* Decorative Wave Background */}
      {/* <div className="absolute top-1/2 left-0 w-full h-full opacity-30 z-0 pointer-events-none flex justify-center items-center">
        <img src={ondaBG} alt="" className="w-full h-auto object-cover opacity-80" />
      </div> */}

      <div className="max-w-6xl mx-auto w-full space-y-8 lg:space-y-16 relative z-10 px-6">
        
        <h2 className="font-['ZT_Nature'] font-thin text-5xl md:text-7xl leading-tight text-right text-[#181818]">
          Uma experiência<br />
          desenhada para quem<br />
          <span className="text-[#b341f2] italic font-['ZT_Nature']">toma as decisões.</span>
        </h2>
        
        {/* Adicionado slide-target aqui para fazer com que os textos e a lista venham da esquerda */}
        <div className="w-full max-w-2xl space-y-4 lg:space-y-8 pt-8 relative z-20 slide-target">
          <p className="font-['Inter'] font-light text-base md:text-lg text-gray-700 leading-relaxed">
            Para garantir o mais alto nível de discussões e networking, o <span className="font-semibold text-black">Vigil Summit é estritamente restrito a 120 participantes.</span>
          </p>
          
          <div className="space-y-4">
            <p className="font-['ZT_Nature'] text-xl md:text-2xl font-bold italic text-black">
              Este evento foi feito para você se você é:
            </p>
            
            <ul className="list-disc list-inside space-y-2 font-['Inter'] text-sm md:text-base font-light text-gray-800 ml-2">
              <li>CISO (Chief Information Security Officer)</li>
              <li>CTO ou CIO</li>
              <li>Diretor ou Gerente de TI</li>
              <li>Head de Gestão de Riscos e Compliance</li>
              <li className="pt-2"><span className="font-medium text-gray-500 italic">Especialmente indicado para líderes de empresas<br/> com mais de 200 colaboradores.</span></li>
            </ul>
          </div>
        </div>
      </div>

      {/* Imagem do Braço IA (Embaixo da partícula) */}
      <div className="absolute right-0 top-4/5 -translate-y-1/2 w-[150px] md:w-[350px] lg:w-[500px] hidden md:block pointer-events-none z-10">
        <img src={bracoIA} alt="Inteligência Artificial" className="w-full object-contain drop-shadow-2xl" />
      </div>

      {/* Orbe de Partículas 3D */}
      <div className="absolute right-0 lg:right-32 top-3/5 -translate-y-1/2 w-[150px] md:w-[350px] lg:w-[450px] h-[150px] md:h-[350px] lg:h-[450px] hidden md:flex pointer-events-auto z-20 justify-end items-center">
        <ParticleOrb />
      </div>
    </section>
  );
}
