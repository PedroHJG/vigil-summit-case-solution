import React from 'react';
import person1 from '../../assets/images/person1.png';
import person2 from '../../assets/images/person2.png';
import person3 from '../../assets/images/person3.png';

export default function SpeakersSection() {
  return (
    <section className="py-24 px-6 relative">
      <div className="max-w-7xl mx-auto space-y-16">
        
        <h2 className="font-['ZT_Nature'] font-thin text-5xl md:text-7xl leading-tight text-center text-[#181818] max-w-4xl mx-auto">
          Aprenda com os <span className="text-[#b341f2] italic font-['ZT_Nature']">maiores<br />especialistas</span> do<br />mercado.
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-8">
          
          <div className="bg-[#484848] text-white rounded-xl overflow-hidden flex flex-col shadow-xl transition-transform hover:-translate-y-2 duration-300">
            <div className="h-64 overflow-hidden relative">
               <img src={person1} alt="Marcos Viana" className="w-full h-full object-cover object-top" />
               <div className="absolute inset-0 bg-gradient-to-t from-[#484848] via-transparent to-transparent"></div>
            </div>
            <div className="p-8 flex-1 flex flex-col text-center">
               <h3 className="font-bold text-sm mb-4">Marcos Viana<br/><span className="text-xs font-light text-gray-300">CEO & Fundador, Vigil.AI</span></h3>
               <p className="font-light text-[11px] leading-relaxed text-gray-400">Keynote: A evolução da segurança reativa para a Defesa Ativa. Saiba como preparar sua infraestrutura para combater ameaças autônomas na era da IA.</p>
            </div>
          </div>

          <div className="bg-[#484848] text-white rounded-xl overflow-hidden flex flex-col shadow-xl transition-transform hover:-translate-y-2 duration-300">
            <div className="h-64 overflow-hidden relative">
               <img src={person2} alt="Dra. Elena Rocha" className="w-full h-full object-cover object-top" />
               <div className="absolute inset-0 bg-gradient-to-t from-[#484848] via-transparent to-transparent"></div>
            </div>
            <div className="p-8 flex-1 flex flex-col text-center">
               <h3 className="font-bold text-sm mb-4">Dra. Elena Rocha<br/><span className="text-xs font-light text-gray-300">Head de Inteligência Artificial, Vigil.AI</span></h3>
               <p className="font-light text-[11px] leading-relaxed text-gray-400">Sessão Técnica: Como nosso motor de Machine Learning analisa milhões de logs em tempo real para eliminar a fadiga de alertas e priorizar riscos reais.</p>
            </div>
          </div>

          <div className="bg-[#484848] text-white rounded-xl overflow-hidden flex flex-col shadow-xl transition-transform hover:-translate-y-2 duration-300">
            <div className="h-64 overflow-hidden relative">
               <img src={person3} alt="Roberto Almeida" className="w-full h-full object-cover object-top" />
               <div className="absolute inset-0 bg-gradient-to-t from-[#484848] via-transparent to-transparent"></div>
            </div>
            <div className="p-8 flex-1 flex flex-col text-center">
               <h3 className="font-bold text-sm mb-4">Roberto Almeida<br/><span className="text-xs font-light text-gray-300">Diretor de GRC, Vigil.AI</span></h3>
               <p className="font-light text-[11px] leading-relaxed text-gray-400">Painel e Demo: Conformidade sem burocracia. Veja ao vivo a automação da coleta de evidências e a geração de relatórios para ISO 27001, LGPD e SOC 2.</p>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
