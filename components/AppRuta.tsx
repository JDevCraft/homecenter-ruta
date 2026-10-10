"use client";

import { useCallback, useRef, useState, type FormEvent } from "react";
import type { ProductoPublico, RespuestaBuscar } from "@/app/api/buscar/route";
import { MOSTRAR_CONTROLES, MOSTRAR_INDICACIONES } from "@/lib/config";
import { MAPA } from "@/lib/mapa";
import { calcularRuta, pasillosDelPlano } from "@/lib/ruta/calcular";
import type { Ruta } from "@/lib/tipos";
import { Mapa, type MapaHandle } from "./Mapa";
import estilos from "./AppRuta.module.css";

const PLANO = new Set(pasillosDelPlano());
const EJEMPLOS = ["pintura blanco almendra", "taladro percutor", "bombillo led", "martillo bola"];

interface Foco {
  /** qué se está mostrando: un resultado y, si se tocó una alternativa, cuál */
  resultado: number;
  alternativa: number | null;
}

export function AppRuta() {
  const mapa = useRef<MapaHandle>(null);
  const campo = useRef<HTMLInputElement>(null);
  const peticion = useRef<AbortController | null>(null);
  const [q, setQ] = useState("");
  const [respuesta, setRespuesta] = useState<RespuestaBuscar | null>(null);
  const [cargando, setCargando] = useState(false);
  const [foco, setFoco] = useState<Foco>({ resultado: 0, alternativa: null });
  const [ruta, setRuta] = useState<Ruta | null>(null);
  const [version, setVersion] = useState(0);
  const [paso, setPaso] = useState({ i: -1, n: 0 });
  const [aviso, setAviso] = useState<string | null>(null);
  const [origen, setOrigen] = useState<string | null>(null);
  const [actual, setActual] = useState("");
  const [errorOrigen, setErrorOrigen] = useState<string | null>(null);
  /** producto de la 2ª búsqueda (o posteriores) a la espera de saber en qué pasillo está el cliente */
  const [pendiente, setPendiente] = useState<ProductoPublico | null>(null);
  const yaHuboRuta = useRef(false);

  /** dibuja la ruta a un pasillo del plano; si el pasillo no está en el plano, solo avisa */
  const mostrarPasillo = useCallback((idPlano: string | null, pasillo: string, origen: string | null) => {
    if (!idPlano) {
      setRuta(null);
      setPaso({ i: -1, n: 0 });
      setAviso(`Este producto está en una zona fuera del plano${pasillo ? ` (pasillo ${pasillo})` : ""}.`);
      return;
    }
    try {
      const r = calcularRuta(idPlano, origen ? { desde: origen } : {});
      setAviso(null);
      setRuta(r);
      yaHuboRuta.current = true;
      setVersion((v) => v + 1);
      setPaso({ i: 0, n: r.tramos.length });
    } catch {
      setRuta(null);
      setAviso("No pude calcular la ruta a ese pasillo.");
    }
  }, []);

  const cerrarPregunta = () => {
    setPendiente(null);
    setActual("");
    setErrorOrigen(null);
  };
  /** el cliente dice en qué pasillo está: la ruta al producto pendiente sale de ahí */
  const fijarOrigen = (e: FormEvent) => {
    e.preventDefault();
    const id = actual.trim().toLowerCase();
    if (!id || !pendiente) return;
    if (!PLANO.has(id)) {
      setErrorOrigen(`No encuentro el pasillo «${actual.trim()}» en el plano. Prueba con uno como 13A.`);
      return;
    }
    setOrigen(id);
    mostrarPasillo(pendiente.idPlano, pendiente.pasillo, id);
    cerrarPregunta();
  };
  /** el cliente sigue en la entrada (o no sabe su pasillo): la ruta sale de la entrada */
  const desdeEntrada = () => {
    if (pendiente) mostrarPasillo(pendiente.idPlano, pendiente.pasillo, null);
    cerrarPregunta();
  };

  const buscar = useCallback(
    async (texto: string) => {
      campo.current?.blur(); // se cierra el teclado y el mapa queda visible
      window.scrollTo(0, 0);
      peticion.current?.abort(); // buscar otra cosa cancela la búsqueda y la animación anteriores
      const control = new AbortController();
      peticion.current = control;
      setRuta(null);
      setPaso({ i: -1, n: 0 });
      setAviso(null);
      setOrigen(null);
      setPendiente(null);
      if (!texto.trim()) {
        setRespuesta(null);
        return;
      }
      setCargando(true);
      try {
        const res = await fetch(`/api/buscar?q=${encodeURIComponent(texto)}`, { signal: control.signal });
        const datos = (await res.json()) as RespuestaBuscar;
        setRespuesta(datos);
        setFoco({ resultado: 0, alternativa: null });
        const primero = datos.resultados[0];
        if (!primero) setAviso(datos.mensaje);
        else if (yaHuboRuta.current && primero.idPlano)
          setPendiente(primero); // 2ª búsqueda en adelante: se pregunta dónde está
        else mostrarPasillo(primero.idPlano, primero.pasillo, null);
      } catch (e) {
        if ((e as Error).name !== "AbortError") setAviso("No pude buscar ahora. Revisa tu conexión e intenta de nuevo.");
      } finally {
        if (peticion.current === control) setCargando(false);
      }
    },
    [mostrarPasillo],
  );

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    void buscar(q);
  };
  const ejemplo = (texto: string) => {
    setQ(texto);
    void buscar(texto);
  };
  const elegir = (n: number, p: ProductoPublico) => {
    setFoco({ resultado: n, alternativa: null });
    mostrarPasillo(p.idPlano, p.pasillo, origen);
  };
  const elegirAlternativa = (n: number, a: number, p: ProductoPublico) => {
    setFoco({ resultado: n, alternativa: a });
    mostrarPasillo(p.alternativas[a].idPlano, p.alternativas[a].pasillo, origen);
  };

  const n = paso.n;
  const textoPaso = ruta && paso.i >= 0 ? ruta.instrucciones[paso.i] : "";
  const etiquetaPaso = paso.i < 0 ? "" : paso.i === n - 1 ? `Llegaste · paso ${n} de ${n}` : `Paso ${paso.i + 1} de ${n}`;

  return (
    <div className={estilos.app}>
      <header className={estilos.arriba}>
        <h1>Homecenter Calle 80 · ¿Qué producto buscas?</h1>
        <form className={estilos.caja} onSubmit={enviar}>
          <input
            ref={campo}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            type="search"
            enterKeyHint="search"
            autoComplete="off"
            autoCapitalize="none"
            placeholder="Ej.: pintura blanco almendra"
            aria-label="Buscar producto"
            maxLength={80}
          />
          <button type="submit" disabled={cargando}>
            {cargando ? "…" : "Buscar"}
          </button>
        </form>
        <div className={estilos.ejemplos}>
          Prueba:{" "}
          {EJEMPLOS.map((t) => (
            <button key={t} type="button" onClick={() => ejemplo(t)}>
              {t}
            </button>
          ))}
        </div>
      </header>

      {respuesta && respuesta.resultados.length > 0 && (
        <section className={estilos.resultados} aria-label="Resultados">
          {respuesta.resultados.map((p, i) => (
            <article key={p.sku} className={`${estilos.tarjeta} ${foco.resultado === i ? estilos.sel : ""}`}>
              <button type="button" className={estilos.producto} onClick={() => elegir(i, p)}>
                <b>{p.descripcion}</b>
                <small>
                  {p.familia} · SKU {p.sku}
                </small>
                <span className={`${estilos.pasillo} ${p.idPlano ? "" : estilos.fuera}`}>
                  {p.pasillo ? `Pasillo ${p.pasillo}` : "Sin pasillo"}
                  {p.idPlano ? "" : " · fuera del plano"}
                </span>
              </button>
              {p.alternativas.length > 0 && (
                <div className={estilos.alternativas}>
                  También en
                  {p.alternativas.slice(0, 3).map((a, k) => (
                    <button
                      key={a.pasillo + k}
                      type="button"
                      className={foco.resultado === i && foco.alternativa === k ? estilos.altSel : ""}
                      onClick={() => elegirAlternativa(i, k, p)}
                    >
                      {a.pasillo}
                      {a.idPlano ? "" : " ✕"}
                    </button>
                  ))}
                </div>
              )}
            </article>
          ))}
        </section>
      )}
      {respuesta && respuesta.resultados.length === 0 && respuesta.sugerencias.length > 0 && (
        <section className={estilos.resultados}>
          <div className={estilos.mensaje}>
            ¿Quisiste decir?
            <div className={estilos.chips}>
              {respuesta.sugerencias.map((s) => (
                <button key={s} type="button" onClick={() => ejemplo(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className={estilos.mapa}>
        <Mapa ref={mapa} ruta={ruta} version={version} desdeEntrada={!origen} alCambiarPaso={(i, total) => setPaso({ i, n: total })} />
        {ruta && (
          <button type="button" className={estilos.verTodo} onClick={() => mapa.current?.verRuta()}>
            Ver ruta completa
          </button>
        )}
      </section>

      <footer className={estilos.panel}>
        {aviso && (
          <div className={estilos.aviso} role="status">
            {aviso}
          </div>
        )}
        {MOSTRAR_INDICACIONES && ruta && paso.i >= 0 && (
          <div className={estilos.paso} aria-live="polite">
            <span>{etiquetaPaso}</span>
            <p>{textoPaso}</p>
          </div>
        )}
        {MOSTRAR_CONTROLES && (
          <div className={estilos.controles}>
            <button type="button" disabled={!ruta || paso.i <= 0} onClick={() => mapa.current?.irPaso(paso.i - 1)}>
              ◀ Paso anterior
            </button>
            <button type="button" className={estilos.principal} disabled={!ruta} onClick={() => setVersion((v) => v + 1)}>
              ↻ Repetir ruta
            </button>
            <button type="button" disabled={!ruta || paso.i >= n - 1} onClick={() => mapa.current?.irPaso(paso.i + 1)}>
              Paso siguiente ▶
            </button>
          </div>
        )}
        <div className={estilos.leyenda}>
          {MAPA.leyenda.map((c) => (
            <span key={c.nombre}>
              <i style={{ background: c.color }} />
              {c.nombre}
            </span>
          ))}
        </div>
      </footer>
      {pendiente && (
        <div className={estilos.fondo}>
          <form className={estilos.dialogo} role="dialog" aria-modal="true" aria-labelledby="titulo-origen" onSubmit={fijarOrigen}>
            <h2 id="titulo-origen">¿Dónde estás?</h2>
            <p>
              Dime en qué pasillo estás ahora y te llevo desde ahí hasta <b>{pendiente.descripcion}</b> (pasillo {pendiente.pasillo}).
            </p>
            <input
              value={actual}
              onChange={(e) => setActual(e.target.value)}
              autoFocus
              autoComplete="off"
              autoCapitalize="characters"
              placeholder="Ej.: 13A"
              aria-label="Pasillo donde estás"
              maxLength={6}
            />
            {errorOrigen && <span role="alert">{errorOrigen}</span>}
            <button type="submit" className={estilos.principal}>
              Calcular ruta desde aquí
            </button>
            <button type="button" onClick={desdeEntrada}>
              Estoy en la entrada
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
