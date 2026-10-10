/** Etiqueta redondeada del mapa. Va girada +90° porque el mapa se muestra girado -90°: el texto queda derecho en pantalla. */
export function Pill({ x, y, texto, fondo, color, tamano = 20, borde }: { x: number; y: number; texto: string; fondo: string; color: string; tamano?: number; borde?: string }) {
  const w = texto.length * tamano * 0.6 + tamano * 0.9;
  const h = tamano * 1.55;
  return (
    <g transform={`rotate(90 ${x} ${y})`}>
      <rect x={x - w / 2} y={y - h / 2} width={w} height={h} rx={h / 2} fill={fondo} stroke={borde} strokeWidth={borde ? 3 : undefined} />
      <text x={x} y={y + tamano * 0.36} textAnchor="middle" fontSize={tamano} fontWeight={700} fill={color}>
        {texto}
      </text>
    </g>
  );
}
