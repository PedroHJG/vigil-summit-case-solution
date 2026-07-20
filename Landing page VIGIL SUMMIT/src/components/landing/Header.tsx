import React, { useState, useEffect } from 'react';
import { scrollToTarget } from '../../utils/scrollTo';

export default function Header() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScrollEvent = () => {
      setIsScrolled(window.scrollY > 20);
    };
    
    window.addEventListener('scroll', handleScrollEvent);
    return () => window.removeEventListener('scroll', handleScrollEvent);
  }, []);

  const handleScroll = (e: React.MouseEvent<HTMLAnchorElement>, target: string) => {
    e.preventDefault();
    scrollToTarget(target);
  };

  return (
    <header className={`fixed top-0 left-0 w-full z-50 flex justify-center transition-all duration-300 ${isScrolled ? 'pt-4' : 'pt-8'}`}>
      <nav 
        className={`flex space-x-12 text-sm md:text-base font-light transition-all duration-500 ${
          isScrolled 
            ? 'px-10 py-4 bg-[#0a0a0a]/50 backdrop-blur-md border border-white/10 shadow-2xl rounded-full text-white' 
            : 'px-6 py-2 bg-transparent text-[#181818]'
        }`}
      >
        <a href="#inicio" onClick={(e) => handleScroll(e, '#inicio')} className="hover:text-[#8d2fc3] transition-colors cursor-pointer">Início</a>
        <a href="#inscricao" onClick={(e) => handleScroll(e, '#inscricao')} className="hover:text-[#8d2fc3] transition-colors cursor-pointer">Inscrição</a>
        <a href="#evento" onClick={(e) => handleScroll(e, '#evento')} className="hover:text-[#8d2fc3] transition-colors cursor-pointer">Evento</a>
      </nav>
    </header>
  );
}
