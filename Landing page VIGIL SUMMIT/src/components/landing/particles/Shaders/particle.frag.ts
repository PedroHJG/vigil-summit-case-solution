export const fragmentShader = `
varying float vAlpha;
varying float vAngle; // Recebido do vertex shader

void main() {
    // Translada coordenadas do ponto para o centro (0, 0)
    vec2 p = gl_PointCoord - vec2(0.5);
    
    // Matriz de Rotação 2D local no fragmento para orientar as partículas
    float s = sin(vAngle);
    float c = cos(vAngle);
    vec2 rotated = vec2(p.x * c - p.y * s, p.x * s + p.y * c);
    
    // Esticamento: Comprime em um eixo para criar formato de "traço" elegante
    rotated.x *= 3.5; 
    
    // Distância após o alongamento para gerar uma elipse
    float d = length(rotated);
    
    // Descarta fragmentos mortos
    if (d > 0.5) discard;
    
    // Suaviza as bordas
    float baseAlpha = smoothstep(0.5, 0.35, d);
    
    // Cor preta com opacidade base global atenuada pelo vAlpha
    float alpha = baseAlpha * vAlpha * 0.5; // Max 0.5
    
    gl_FragColor = vec4(0.0, 0.0, 0.0, alpha); // Preto
}
`;
