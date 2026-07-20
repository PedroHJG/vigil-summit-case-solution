import { gsap } from 'gsap';
import { ScrollToPlugin } from 'gsap/ScrollToPlugin';

gsap.registerPlugin(ScrollToPlugin);

export const scrollToTarget = (target: string) => {
  if (target === "#inscricao") {
    gsap.to(window, { duration: 1, scrollTo: { y: target, offsetY: -140 }, ease: "power2.inOut" });
  } else {
    gsap.to(window, { duration: 1, scrollTo: target, ease: "power2.inOut" });
  }
};
