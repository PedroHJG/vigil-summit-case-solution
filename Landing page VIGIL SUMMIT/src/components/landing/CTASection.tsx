import React, { useRef } from 'react';
import { scrollToTarget } from '../../utils/scrollTo';
import { useTypewriter, useSlideIn } from '../../utils/animations';

export default function CTASection() {
  const containerRef = useRef<HTMLElement>(null);
  
  // Aplica o typewriter apenas no primeiro parágrafo
  useTypewriter(containerRef, '.typewriter-target');
  
  // Aplica o slide vindo de baixo para o bloco do botão
  useSlideIn(containerRef, '.slide-target', 'up');

  return (
    <section ref={containerRef} className="py-24 px-6 relative text-center flex flex-col items-center">
      <div className="max-w-4xl mx-auto space-y-8 relative z-10 text-left w-full">
        <h2 className="font-['ZT_Nature'] font-thin text-5xl md:text-7xl leading-tight text-[#181818]">
          Apenas <span className="text-[#d93535] italic font-['ZT_Nature']">120 lugares</span><br />
          disponíveis para o futuro da cibersegurança.
        </h2>
        
        {/* Marcado para typewriter */}
        <p className="typewriter-target font-['Inter'] font-light text-sm md:text-base text-gray-600 max-w-2xl leading-relaxed">
          As vagas para o Vigil Summit <span className="font-semibold text-black">são preenchidas rapidamente</span> por convite e solicitação. Não perca a oportunidade de descobrir como blindar sua infraestrutura na era da IA e conectar-se com a elite da tecnologia nacional.
        </p>
      </div>

      {/* Marcado para vir de baixo para cima */}
      <div className="slide-target pt-16 pb-8 w-full max-w-4xl flex flex-col items-center">
        <button className="bg-[#484848] text-white px-10 py-4 rounded-lg hover:bg-[#383838] transition-colors cursor-pointer border-none font-['Inter'] font-medium text-sm shadow-xl" onClick={() => scrollToTarget('#inscricao')}>
          Enviar Solicitação de Convite
        </button>
        <p className="text-gray-400 text-[10px] mt-4 font-light max-w-md mx-auto text-center">
          A solicitação não garante a vaga. Todas as inscrições passarão por uma curadoria para garantir a sinergia do grupo.
        </p>
      </div>
    </section>
  );
}
