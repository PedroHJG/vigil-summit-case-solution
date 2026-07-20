import React, { useState } from 'react';
import formBg from '../../assets/images/formBG.jpg';
import formBgMobile from '../../assets/images/formBGmobile.png';
import Lock3D from './3d/Lock3D';

export default function InscricaoSection() {
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    ddi: '+55',
    telefone: '',
    cargo: '',
    empresa: ''
  });

  const [touched, setTouched] = useState({
    nome: false,
    email: false,
    ddi: false,
    telefone: false,
    cargo: false,
    empresa: false
  });

  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [submitResult, setSubmitResult] = useState<{ ok: boolean; message: string } | null>(null);

  // Sem VITE_API_URL definida, aponta para o backend no MESMO host que serviu a
  // página — funciona no PC (localhost) e em celulares na rede local (192.168.x.x),
  // onde "localhost" seria o próprio celular.
  const API_URL =
    import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`;

  const freeEmailDomains = [
    'gmail.com', 'yahoo.com', 'yahoo.com.br', 'hotmail.com', 
    'outlook.com', 'uol.com.br', 'bol.com.br', 'icloud.com', 
    'msn.com', 'live.com', 'terra.com.br', 'ig.com.br'
  ];
  
  const isCorporateEmail = (email: string) => {
    if (!email) return false;
    const domain = email.split('@')[1];
    return domain && !freeEmailDomains.includes(domain.toLowerCase());
  };

  const telefoneRegex = /^\(\d{2}\)\s9\s\d{4}-\d{4}$/;

  const errors = {
    nome: !formData.nome.trim() 
      ? 'O nome completo é obrigatório.' 
      : (formData.nome.trim().split(/\s+/).length < 2 ? 'Insira seu nome e sobrenome.' : ''),
      
    email: !formData.email.trim() 
      ? 'O e-mail corporativo é obrigatório.' 
      : (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) 
          ? 'Insira um e-mail válido.' 
          : (!isCorporateEmail(formData.email) ? 'Utilize um e-mail corporativo (não utilize Gmail, Outlook, etc).' : '')),
          
    ddi: !formData.ddi.trim() ? 'Obrigatório.' : '',
          
    telefone: !formData.telefone.trim() 
      ? 'O telefone/whatsapp é obrigatório.' 
      : (!telefoneRegex.test(formData.telefone) ? 'Siga o padrão: (11) 9 9999-9999' : ''),
      
    cargo: formData.cargo ? '' : 'Selecione um cargo.',
    empresa: formData.empresa.trim() ? '' : 'O nome da empresa é obrigatório.'
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let { value } = e.target;
    let v = value.replace(/\D/g, "");
    if (v.length > 11) v = v.slice(0, 11);

    let formatted = v;
    if (v.length > 0) {
      if (v.length <= 2) {
        formatted = `(${v}`;
      } else if (v.length <= 3) {
        formatted = `(${v.slice(0, 2)}) ${v.slice(2)}`;
      } else if (v.length <= 7) {
        formatted = `(${v.slice(0, 2)}) ${v.slice(2, 3)} ${v.slice(3)}`;
      } else {
        formatted = `(${v.slice(0, 2)}) ${v.slice(2, 3)} ${v.slice(3, 7)}-${v.slice(7)}`;
      }
    }
    
    setFormData(prev => ({ ...prev, telefone: formatted }));
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);
    setSubmitResult(null);

    const hasErrors = Object.values(errors).some(error => error !== '');
    if (hasErrors || isSending) return;

    setIsSending(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setSubmitResult({
          ok: true,
          message: 'Solicitação recebida! Em breve nosso time entra em contato pelo WhatsApp.',
        });
        setFormData({ nome: '', email: '', ddi: '+55', telefone: '', cargo: '', empresa: '' });
        setTouched({ nome: false, email: false, ddi: false, telefone: false, cargo: false, empresa: false });
        setIsSubmitted(false);
      } else if (response.status === 409) {
        setSubmitResult({ ok: false, message: 'Este e-mail já está inscrito no evento.' });
      } else {
        const body = await response.json().catch(() => null);
        const detail = typeof body?.detail === 'string' ? body.detail : 'Verifique os dados e tente novamente.';
        setSubmitResult({ ok: false, message: detail });
      }
    } catch {
      setSubmitResult({
        ok: false,
        message: 'Não foi possível enviar agora. Tente novamente em instantes.',
      });
    } finally {
      setIsSending(false);
    }
  };

  const getInputClasses = (fieldName: keyof typeof errors) => {
    const hasError = (touched[fieldName] || isSubmitted) && errors[fieldName];
    return `w-full bg-transparent border-b pb-3 text-white placeholder-gray-400 outline-none transition-colors text-sm ${
      hasError 
        ? 'border-red-500 focus:border-red-500' 
        : 'border-gray-500 focus:border-[#8d2fc3]'
    }`;
  };

  const renderError = (fieldName: keyof typeof errors) => {
    const hasError = (touched[fieldName] || isSubmitted) && errors[fieldName];
    // Não renderizar mensagem para DDI para não quebrar o layout, ele só fica com a borda vermelha.
    if (hasError && fieldName !== 'ddi') {
      return <p className="text-red-500 text-xs mt-1">{errors[fieldName]}</p>;
    }
    return null;
  };

  return (
    <section id="inscricao" className="w-full flex flex-col items-center overflow-hidden">
      {/* Dark Transition & Form Area */}
      <div className="w-full relative mt-24 min-h-screen">
        {/* Background Image formBG */}
        <div className="absolute top-0 left-0 w-full h-full z-0">
          <div className="absolute inset-0 overflow-hidden">
            <img
              src={formBg}
              alt="Background Desktop"
              className="hidden md:block object-cover object-center w-full h-full"
            />
            <img
              src={formBgMobile}
              alt="Background Mobile"
              className="md:hidden object-cover object-center w-full h-full"
            />
            <div
              className="absolute inset-0 shadow-[inset_0px_146px_34.9px_0px_rgba(0,0,0,1)] pointer-events-none"
            />
          </div>
        </div>

        {/* Soft white gradient fading out to transparent (100% to 0%) */}
        <div className="absolute top-0 left-0 w-full overflow-hidden z-10">
          <svg viewBox="0 0 1440 520" className="w-full h-[100px]" preserveAspectRatio="none">
            <defs>
              <radialGradient id="waveFade" cx="720" cy="-2090" r="2302" gradientUnits="userSpaceOnUse">
                <stop offset="96%" stopColor="#ffffff" stopOpacity="1" />
                <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
              </radialGradient>
            </defs>
            <path fill="url(#waveFade)" d="M0,0L1440,0L1440,96C1200,250,240,250,0,96Z" />
          </svg>
        </div>
      
        <div className="relative z-20 max-w-5xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-0 items-center pt-32 pb-32">
          
          {/* Left Content: Form */}
          <div className="relative z-20 bg-[rgba(255,255,255,0.05)] backdrop-blur-xl border border-[rgba(255,255,255,0.1)] rounded-2xl p-8 lg:p-10 shadow-[0_8px_32px_rgba(0,0,0,0.37)] w-full max-w-md mx-auto lg:mr-auto lg:ml-0">
            <form className="space-y-6" onSubmit={handleSubmit} noValidate>
              <div>
                <input 
                  type="text" 
                  name="nome"
                  value={formData.nome}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  placeholder="Nome Completo *" 
                  className={getInputClasses('nome')} 
                />
                {renderError('nome')}
              </div>
              <div>
                <input 
                  type="email" 
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  placeholder="E-mail Corporativo *" 
                  className={getInputClasses('email')} 
                />
                {renderError('email')}
              </div>
              
              <div className="flex gap-4">
                <div className="w-16">
                  <input 
                    type="text" 
                    name="ddi"
                    value={formData.ddi}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder="+55" 
                    className={getInputClasses('ddi')} 
                  />
                </div>
                <div className="flex-1">
                  <input 
                    type="tel" 
                    name="telefone"
                    value={formData.telefone}
                    onChange={handlePhoneChange}
                    onBlur={handleBlur}
                    placeholder="Telefone/Whatsapp *" 
                    className={getInputClasses('telefone')} 
                  />
                  {renderError('telefone')}
                </div>
              </div>

              <div>
                <select 
                  name="cargo"
                  value={formData.cargo}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  className={`${getInputClasses('cargo')} appearance-none cursor-pointer`}
                >
                  <option value="" disabled className="bg-[#1a1a1a] text-gray-400">Cargo *</option>
                  <option value="CTO" className="bg-[#1a1a1a] text-white">CTO</option>
                  <option value="CISO" className="bg-[#1a1a1a] text-white">CISO</option>
                  <option value="Diretor de TI" className="bg-[#1a1a1a] text-white">Diretor de TI</option>
                  <option value="Gestor de Risco" className="bg-[#1a1a1a] text-white">Gestor de Risco</option>
                  <option value="Outros" className="bg-[#1a1a1a] text-white">Outros</option>
                </select>
                {renderError('cargo')}
              </div>
              <div>
                <input 
                  type="text" 
                  name="empresa"
                  value={formData.empresa}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  placeholder="Nome da empresa *" 
                  className={getInputClasses('empresa')} 
                />
                {renderError('empresa')}
              </div>
              
              <button
                type="submit"
                disabled={isSending}
                className="w-full bg-gradient-to-r from-[#b341f2] to-[#8d2fc3] h-12 rounded-xl hover:opacity-90 transition-opacity cursor-pointer border-none font-['Inter'] font-medium text-sm text-white mt-8 shadow-[0_4px_20px_rgba(141,47,195,0.4)] disabled:opacity-60 disabled:cursor-wait"
              >
                {isSending ? 'Enviando...' : 'Enviar Solicitação de Convite'}
              </button>

              {submitResult && (
                <p
                  className={`text-xs text-center pt-1 ${submitResult.ok ? 'text-green-400' : 'text-red-400'}`}
                  role="status"
                >
                  {submitResult.message}
                </p>
              )}

              <p className="text-gray-300 text-[10px] text-center pt-2">Seus dados estão seguros. Não enviamos spam.</p>
            </form>
          </div>

          {/* Right Content: Lock 3D (Overlapping the form with higher z-index) */}
          <div className="relative hidden lg:flex justify-end lg:ml-4 z-30 mt-12 lg:mt-0 w-full md:w-[650px] h-[500px] md:h-[650px] lg:-mr-12">
            {/* The negative margin left on lg pulls it over the form */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-[#b341f2] blur-[100px] opacity-30 z-0 pointer-events-none"></div>
            <Lock3D />
          </div>

        </div>
      </div>
    </section>
  );
}
