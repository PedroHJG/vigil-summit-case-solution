import { useEffect, RefObject } from 'react';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export function useTypewriter(containerRef: RefObject<HTMLElement>, selector: string) {
  useEffect(() => {
    if (!containerRef.current) return;
    const ctx = gsap.context(() => {}, containerRef);

    // Timeout para garantir que o DOM renderizou
    const timeout = setTimeout(() => {
      const elements = Array.from(containerRef.current!.querySelectorAll(selector));
      if (elements.length === 0) return;

      elements.forEach(el => {
        const textNodes: Node[] = [];
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
        let node;
        while ((node = walker.nextNode())) {
          if (node.nodeValue && node.nodeValue.trim() !== '') {
            textNodes.push(node);
          }
        }

        const charSpans: HTMLSpanElement[] = [];
        textNodes.forEach(textNode => {
          const text = textNode.nodeValue || '';
          const fragment = document.createDocumentFragment();
          
          // Otimização: Separar por palavras em vez de caracteres para reduzir drasticamente 
          // o número de nós no DOM e evitar travamentos na animação (stuttering).
          const words = text.split(/(\s+)/);
          words.forEach(word => {
            if (word.trim() === '') {
               fragment.appendChild(document.createTextNode(word));
            } else {
               const span = document.createElement('span');
               span.textContent = word;
               span.style.opacity = '0';
               span.style.display = 'inline-block'; // Garante que a opacidade funcione bem
               fragment.appendChild(span);
               charSpans.push(span);
            }
          });
          textNode.parentNode?.replaceChild(fragment, textNode);
        });

        if (charSpans.length > 0) {
          ctx.add(() => {
            gsap.to(charSpans, {
              opacity: 1,
              duration: 0.1,
              stagger: 0.04, // Ajustado para palavras
              scrollTrigger: {
                trigger: el,
                start: "top 85%",
                once: true
              }
            });
          });
        }
      });
      // refresh() apenas quando o layout muda de fato (montagem), nunca em
      // resize contínuo — o ScrollTrigger já cuida do debounce interno.
      ScrollTrigger.refresh();
    }, 100);

    return () => {
      clearTimeout(timeout);
      // Kill/Revert: mata tweens e ScrollTriggers criados neste escopo,
      // evitando vazamento e lentidão cumulativa em re-montagens.
      ctx.revert();
    };
  }, [containerRef, selector]);
}

export function useSlideIn(containerRef: RefObject<HTMLElement>, selector: string, direction: 'left' | 'up' = 'up') {
  useEffect(() => {
    if (!containerRef.current) return;
    const ctx = gsap.context(() => {}, containerRef);

    const timeout = setTimeout(() => {
      const elements = Array.from(containerRef.current!.querySelectorAll(selector));
      if (elements.length === 0) return;

      const xOffset = direction === 'left' ? -50 : 0;
      const yOffset = direction === 'up' ? 50 : 0;

      elements.forEach(el => {
         ctx.add(() => {
            // autoAlpha (opacity + visibility) tira o elemento oculto do fluxo
            // de pintura; x/y viram transforms acelerados por GPU.
            gsap.fromTo(el,
               { autoAlpha: 0, x: xOffset, y: yOffset },
               {
                  autoAlpha: 1,
                  x: 0,
                  y: 0,
                  duration: 0.8,
                  ease: "power3.out",
                  scrollTrigger: {
                     trigger: el,
                     start: "top 85%",
                     once: true
                  }
               }
            );
         });
      });
      ScrollTrigger.refresh();
    }, 100);

    return () => {
      clearTimeout(timeout);
      ctx.revert();
    };
  }, [containerRef, selector, direction]);
}
