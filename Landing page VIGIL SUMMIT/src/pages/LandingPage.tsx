import React from 'react';
import Header from '../components/landing/Header';
import HeroSection from '../components/landing/HeroSection';
import InscricaoSection from '../components/landing/InscricaoSection';
import ProblemSection from '../components/landing/ProblemSection';
import FeaturesSection from '../components/landing/FeaturesSection';
import SpeakersSection from '../components/landing/SpeakersSection';
import AudienceSection from '../components/landing/AudienceSection';
import CTASection from '../components/landing/CTASection';
import Footer from '../components/landing/Footer';

export default function LandingPage() {
  return (
    <div className="bg-white min-h-screen text-[#181818] font-['Inter'] relative overflow-x-hidden selection:bg-[#8d2fc3] selection:text-white">
      <Header />
      <HeroSection />
      <InscricaoSection />
      <ProblemSection />
      <FeaturesSection />
      <AudienceSection />
      <SpeakersSection />
      <CTASection />
      <Footer />
    </div>
  );
}
