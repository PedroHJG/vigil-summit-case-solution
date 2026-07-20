import React from 'react';
import ondaBG from '../../assets/images/wave.png';

export default function FeaturesSection() {
  return (
    <section className="relative py-24 px-6">
      {/* Decorative Wave Background on the right */}
      <div className="absolute bottom-0 md:bottom-[-10%] -right-24 md:-right-50 w-[300px] md:w-[450px] lg:w-[600px] z-0 pointer-events-none  scale-x-[-1] rotate-330">
        <img src={ondaBG} alt="Ondas" className="w-full h-auto"/>
      </div>

      <div className="max-w-5xl mx-auto space-y-16 relative z-10">
        <h2 className="font-['ZT_Nature'] font-thin text-5xl md:text-7xl leading-tight text-right text-[#181818]">
          Uma <span className="text-[#b341f2] italic font-['ZT_Nature']">imersão prática</span> em<br />
          Segurança Cibernética<br />
          Avançada
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          
          {/* Left Column: 3 stacked blocks */}
          <div className="md:col-span-6 flex flex-col gap-6">
            <div className="bg-[#484848] text-white rounded-xl p-8 shadow-lg transition-transform">
              <p className="font-['Inter'] text-sm font-light leading-relaxed">
                <span className="font-bold text-[#d49ef4]">Monitoramento Contínuo:</span> Como obter visibilidade 360º da sua superfície de ataque com dashboards em tempo real.
              </p>
            </div>
            
            <div className="bg-[#484848] text-white rounded-xl p-8 shadow-lg transition-transform">
              <p className="font-['Inter'] text-sm font-light leading-relaxed">
                <span className="font-bold text-[#d49ef4]">Inteligência Artificial na Prática:</span> Demonstrações ao vivo de como a IA da Vigil prioriza riscos reais e antecipa ameaças antes que se tornem incidentes.
              </p>
            </div>
            
            <div className="bg-[#484848] text-white rounded-xl p-8 shadow-lg transition-transform">
              <p className="font-['Inter'] text-sm font-light leading-relaxed">
                <span className="font-bold text-[#d49ef4]">Conformidade sem Estresse:</span> Estratégias para automatizar relatórios de ISO 27001, LGPD e SOC 2, reduzindo o tempo de auditoria em até 70%.
              </p>
            </div>
          </div>

          {/* Right Column: 1 large block */}
          <div className="md:col-span-6 flex">
            <div className="w-full bg-[#484848] text-white rounded-xl p-10 shadow-lg relative overflow-hidden flex flex-col transition-transform">
              <p className="font-['Inter'] text-sm font-light leading-relaxed relative z-10">
                <span className="font-bold text-[#d49ef4]">Networking de Alto Nível:</span> Troca de experiências com outros CISOs, CTOs e Diretores que enfrentam os mesmos desafios em empresas de grande porte.
              </p>
              {/* Huge watermark text */}
              <div className="absolute left-4 bottom-20 right-4 z-0 pointer-events-none h-32 flex items-end">
                <span className="hidden md:block text-[#3a3a3a] font-['ZT_Nature'] font-black text-[120px] leading-[0.8] tracking-tighter opacity-70 w-full text-center">
                  Vigil.AI
                </span>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  );
}
