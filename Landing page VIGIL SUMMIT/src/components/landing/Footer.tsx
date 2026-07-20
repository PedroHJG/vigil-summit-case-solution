import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-[#484848] text-white pt-16 pb-8 px-6 lg:px-16 relative overflow-hidden">
      
      <div className="relative z-10 max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
        
        <div className="flex flex-col text-left space-y-2">
          <h2 className="font-['ZT_Nature'] text-5xl md:text-6xl font-thin tracking-tight">Vigil.AI</h2>
          <p className="font-light text-[10px] text-gray-400">
            Proteção Inteligente contra ameaças.
          </p>
        </div>
        
        <div className="flex flex-col text-left space-y-1 text-[11px] font-light text-gray-300">
          <a href="mailto:eventos@vigil.ai" className="hover:text-white transition-colors">
            eventos@vigil.ai
          </a>
          <a className="hover:text-white transition-colors">11 99999-9999</a>
          <a href="" className="hover:text-white transition-colors">
            @vigil.ai
          </a>
        </div>
      </div>
    </footer>
  );
}
