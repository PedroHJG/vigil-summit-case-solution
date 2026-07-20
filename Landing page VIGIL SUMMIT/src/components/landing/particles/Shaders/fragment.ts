export const fragmentShader = `
varying float vOpacity;

void main() {
    // Distância do centro do ponto gl_PointCoord (0.5, 0.5 é o centro)
    float dist = distance(gl_PointCoord, vec2(0.5));
    
    // Descarta fragmentos fora do círculo
    if (dist > 0.5) discard;
    
    // Bordas muito suaves para visual premium e elegante
    float alpha = smoothstep(0.5, 0.1, dist) * vOpacity;
    
    // Cor elegante: roxo do tema (#8d2fc3 -> r: 141, g: 47, b: 195 convertido para 0-1)
    vec3 color = vec3(0.553, 0.184, 0.765);
    
    gl_FragColor = vec4(color, alpha);
}
`;
