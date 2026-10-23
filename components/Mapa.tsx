"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Animador } from "@/lib/animacion/animador";
import { Camara } from "@/lib/animacion/camara";
import { Polilinea, crearProyeccion } from "@/lib/animacion/geometria";
import { cajaFusionada } from "@/lib/ruta/instrucciones";
import { MAPA } from "@/lib/mapa";
import type { Punto, Ruta } from "@/lib/tipos";
import { MapaBase } from "./MapaBase";
import { Pill } from "./Pill";
import estilos from "./Mapa.module.css";

export interface MapaHandle {
  irPaso(i: number): void;
  verRuta(): void;
  saltar(): void;
}

interface Props {
  /** ruta a dibujar; null = solo el mapa */
  ruta: Ruta | null;
  /** cambia para repetir la animación de la misma ruta */
  version: number;
  alCambiarPaso(i: number, n: number): void;
  /** true: la ruta sale de la entrada; false: sale del pasillo donde dice estar el cliente */
  desdeEntrada?: boolean;
}

const sinMovimiento = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const aPantalla = crearProyeccion(MAPA.F);
const { navy, amarillo } = MAPA.colores;

/** guarda y restaura los atributos que cambia el resaltado de la góndola destino */
function crearResaltador(svg: SVGSVGElement, mueble: string) {
  const buscar = (prefijo: string) => svg.querySelector<SVGElement>(`[id="${prefijo}-${mueble}"]`);
  const g = buscar("g");
  const l = buscar("l");
  const v = buscar("v");
  // la parte del fondo del pasillo (góndola aparte en el plano) se resalta junto con la de enfrente
  const partes = [...svg.querySelectorAll<SVGElement>(`rect[data-parte="${mueble}"]`)];
  const lr = l?.querySelector("rect") ?? null;
  const lt = l?.querySelector("text") ?? null;
  const guardado = {
    g: g ? [g.getAttribute("fill"), g.getAttribute("stroke"), g.getAttribute("stroke-width")] : null,
    lr: lr ? [lr.getAttribute("fill"), lr.getAttribute("stroke"), lr.getAttribute("stroke-width")] : null,
    lt: lt?.getAttribute("fill") ?? null,
    v: v?.style.display ?? "",
  };
  const poner = (e: Element, nombre: string, valor: string | null) =>
    valor === null ? e.removeAttribute(nombre) : e.setAttribute(nombre, valor);
  return (on: boolean) => {
    if (on) {
      for (const p of partes) {
        if (p.id.startsWith("v-")) p.style.display = "none";
        else {
          p.setAttribute("fill", amarillo);
          p.setAttribute("stroke", navy);
          p.setAttribute("stroke-width", "4");
        }
      }
      g?.setAttribute("fill", amarillo);
      g?.setAttribute("stroke", navy);
      g?.setAttribute("stroke-width", "4");
      lr?.setAttribute("fill", amarillo);
      lr?.setAttribute("stroke", navy);
      lr?.setAttribute("stroke-width", "3");
      lt?.setAttribute("fill", navy);
      if (v) v.style.display = "none";
    } else {
      for (const p of partes) {
        if (p.id.startsWith("v-")) p.style.display = "";
        else {
          p.setAttribute("fill", "#D9E4F1");
          p.removeAttribute("stroke");
          p.removeAttribute("stroke-width");
        }
      }
      if (g && guardado.g) ["fill", "stroke", "stroke-width"].forEach((n, i) => poner(g, n, (guardado.g as (string | null)[])[i]));
      if (lr && guardado.lr) ["fill", "stroke", "stroke-width"].forEach((n, i) => poner(lr, n, (guardado.lr as (string | null)[])[i]));
      if (lt) poner(lt, "fill", guardado.lt);
      if (v) v.style.display = guardado.v;
    }
  };
}

/** Mapa de la tienda (SVG de React) con la ruta dibujada encima y la cámara sobre el viewBox. */
export const Mapa = forwardRef<MapaHandle, Props>(function Mapa({ ruta, version, alCambiarPaso, desdeEntrada = true }, ref) {
  const contenedor = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const capa = useRef<SVGGElement>(null);
  const camara = useRef<Camara | null>(null);
  const animador = useRef<Animador | null>(null);
  const verTodo = useRef(true); // sin ruta, el mapa completo se reajusta cuando cambia el tamaño del contenedor
  const aviso = useRef(alCambiarPaso);
  aviso.current = alCambiarPaso;

  useImperativeHandle(ref, () => ({
    irPaso: (i) => animador.current?.irPaso(i),
    verRuta: () => animador.current?.verRuta(),
    saltar: () => animador.current?.saltar(),
  }));

  // cámara y gestos: una vez
  useEffect(() => {
    const svg = svgRef.current;
    const wrap = contenedor.current;
    if (!svg || !wrap) return;
    const c = new Camara(svg, wrap, MAPA.viewBox, sinMovimiento);
    camara.current = c;
    const quitar = c.gestos(() => animador.current?.saltar()); // tocar el mapa durante la animación la salta al final
    const ro = new ResizeObserver(() => c.fijar(verTodo.current ? c.completa() : c.vista));
    ro.observe(wrap);
    return () => {
      quitar();
      ro.disconnect();
      c.parar();
      camara.current = null;
    };
  }, []);

  // animación: al cambiar la ruta (o repetirla)
  useEffect(() => {
    const c = camara.current;
    const g = capa.current;
    const svg = svgRef.current;
    if (!c || !g || !svg) return;
    verTodo.current = !ruta;
    if (!ruta) {
      c.irA(c.completa(), 0);
      return;
    }
    const el = <T extends Element>(nombre: string) => g.querySelector<T>(`[data-r="${nombre}"]`) as T;
    const gb = cajaFusionada(ruta.mueble);
    const finales: Punto[] = [
      ...ruta.puntos,
      [gb[0], gb[1]],
      [gb[2], gb[3]],
      ...(desdeEntrada
        ? ([
            [MAPA.ent.x + 66, MAPA.ent.y - 75],
            [MAPA.ent.x + 66, MAPA.ent.y + 75],
          ] as Punto[])
        : []),
    ];
    const a = new Animador({
      ruta,
      camara: c,
      elementos: {
        fantasma: el<SVGPathElement>("fantasma"),
        base: el("base"),
        linea: el("linea"),
        tramo: el("tramo"),
        punta: el("punta"),
        destino: el("destino"),
      },
      aPantalla,
      puntosFinales: finales,
      sinMovimiento,
      resaltar: crearResaltador(svg, ruta.mueble),
      alCambiarPaso: (i, n) => aviso.current(i, n),
    });
    animador.current = a;
    a.iniciar();
    return () => {
      a.destruir();
      if (animador.current === a) animador.current = null;
    };
  }, [ruta, version, desdeEntrada]);

  const d = ruta ? new Polilinea(ruta.puntos).trazo() : "";
  const fin = ruta ? ruta.puntos[ruta.puntos.length - 1] : null;
  const ini = ruta ? ruta.puntos[0] : null;
  const [vx, vy, vw, vh] = MAPA.viewBox;

  return (
    <div ref={contenedor} className={estilos.contenedor}>
      <svg ref={svgRef} className={estilos.svg} viewBox={`${vx} ${vy} ${vw} ${vh}`} role="img" aria-label="Mapa de la tienda">
        <MapaBase />
        <g ref={capa} transform={MAPA.rotm}>
          {ruta && fin && ini && (
            <g key={`${ruta.destino}-${ruta.cara}-${version}`}>
              <path
                data-r="fantasma"
                d={d}
                fill="none"
                stroke="#6aa9e6"
                strokeWidth={9}
                strokeLinecap="round"
                strokeDasharray="1 20"
                opacity={0.9}
              />
              <path
                data-r="base"
                d={d}
                fill="none"
                stroke="#fff"
                strokeWidth={17}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0.92}
              />
              <path data-r="linea" d={d} fill="none" stroke={navy} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" />
              <path
                data-r="tramo"
                d={d}
                fill="none"
                stroke={navy}
                strokeWidth={15}
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ display: "none" }}
              />
              <g data-r="destino" style={{ display: "none" }}>
                <circle className="pulso" cx={fin[0]} cy={fin[1]} r={15} fill="none" stroke={amarillo} strokeWidth={6} />
                <circle cx={fin[0]} cy={fin[1]} r={15} fill={amarillo} stroke={navy} strokeWidth={5} />
                <circle cx={fin[0]} cy={fin[1]} r={5} fill={navy} />
                {ruta.ladoContrario && (
                  <Pill x={fin[0]} y={fin[1] - 44} texto="Lado contrario" fondo="#fff" color={navy} borde={amarillo} />
                )}
              </g>
              <g data-r="punta" transform={`translate(${ini[0]} ${ini[1]})`}>
                <circle className="halo" r={20} fill={navy} opacity={0.22} />
                <circle r={9} fill={navy} stroke="#fff" strokeWidth={4} />
              </g>
              <circle cx={ini[0]} cy={ini[1]} r={17} fill={navy} stroke="#fff" strokeWidth={6} />
              {desdeEntrada ? (
                <>
                  <line x1={ini[0]} y1={ini[1] - 14} x2={ini[0]} y2={MAPA.ent.y + 16} stroke={navy} strokeWidth={4} />
                  <Pill x={MAPA.ent.x + 66} y={MAPA.ent.y} texto="Estás aquí" fondo={navy} color="#fff" />
                </>
              ) : (
                <Pill x={ini[0]} y={ini[1] + 46} texto="Estás aquí" fondo={navy} color="#fff" />
              )}
            </g>
          )}
        </g>
      </svg>
    </div>
  );
});
