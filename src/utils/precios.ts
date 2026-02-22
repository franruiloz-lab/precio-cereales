import cerealesData from '../data/cereales.json';
import lonjasData from '../data/lonjas.json';

// Import all weekly price files
const preciosModules = import.meta.glob('../data/precios/**/*.json', { eager: true });

export interface PrecioItem {
  precio: number;
  anterior: number;
  variacion: number;
}

export interface SemanaData {
  semana: number;
  anio: number;
  campania: string;
  fechaInicio: string;
  fechaFin: string;
  precios: Record<string, Record<string, PrecioItem>>;
}

export interface Cereal {
  id: string;
  nombre: string;
  nombreCompleto: string;
  slug: string;
  descripcion: string;
  unidad: string;
  keywords: string[];
  volumenBusqueda: number;
  color: string;
}

export interface Lonja {
  id: string;
  nombre: string;
  slug: string;
  ciudad: string;
  comunidad: string;
  direccion: string;
  telefono: string;
  web: string;
  diaSesion: string;
  descripcion: string;
  cereales: string[];
}

export function getCereales(): Cereal[] {
  return cerealesData as Cereal[];
}

export function getCereal(id: string): Cereal | undefined {
  return (cerealesData as Cereal[]).find(c => c.id === id);
}

export function getLonjas(): Lonja[] {
  return lonjasData as Lonja[];
}

export function getLonja(id: string): Lonja | undefined {
  return (lonjasData as Lonja[]).find(l => l.id === id);
}

export function getTodasLasSemanas(): SemanaData[] {
  const semanas: SemanaData[] = [];
  for (const [, mod] of Object.entries(preciosModules)) {
    semanas.push((mod as { default: SemanaData }).default ?? mod as SemanaData);
  }
  return semanas.sort((a, b) => {
    if (a.anio !== b.anio) return b.anio - a.anio;
    return b.semana - a.semana;
  });
}

export function getSemanaActual(): SemanaData {
  const semanas = getTodasLasSemanas();
  return semanas[0];
}

export function getSemanaAnterior(): SemanaData | undefined {
  const semanas = getTodasLasSemanas();
  return semanas[1];
}

export function getPrecioMedioCereal(semana: SemanaData, cerealId: string): { media: number; min: number; max: number; minLonja: string; maxLonja: string; count: number } | null {
  const precios: { precio: number; lonjaId: string }[] = [];

  for (const [lonjaId, productos] of Object.entries(semana.precios)) {
    const item = productos[cerealId];
    if (item) {
      precios.push({ precio: item.precio, lonjaId });
    }
  }

  if (precios.length === 0) return null;

  const media = precios.reduce((sum, p) => sum + p.precio, 0) / precios.length;
  const minItem = precios.reduce((min, p) => p.precio < min.precio ? p : min, precios[0]);
  const maxItem = precios.reduce((max, p) => p.precio > max.precio ? p : max, precios[0]);

  return {
    media: Math.round(media * 100) / 100,
    min: minItem.precio,
    max: maxItem.precio,
    minLonja: minItem.lonjaId,
    maxLonja: maxItem.lonjaId,
    count: precios.length,
  };
}

export function getVariacionMediaCereal(semana: SemanaData, cerealId: string): number {
  let total = 0;
  let count = 0;

  for (const productos of Object.values(semana.precios)) {
    const item = productos[cerealId];
    if (item) {
      total += item.variacion;
      count++;
    }
  }

  return count > 0 ? Math.round((total / count) * 100) / 100 : 0;
}

export function getPreciosCerealPorLonja(semana: SemanaData, cerealId: string): { lonjaId: string; lonjaNombre: string; precio: number; anterior: number; variacion: number }[] {
  const result: { lonjaId: string; lonjaNombre: string; precio: number; anterior: number; variacion: number }[] = [];

  for (const [lonjaId, productos] of Object.entries(semana.precios)) {
    const item = productos[cerealId];
    if (item) {
      const lonja = getLonja(lonjaId);
      result.push({
        lonjaId,
        lonjaNombre: lonja?.nombre ?? lonjaId,
        precio: item.precio,
        anterior: item.anterior,
        variacion: item.variacion,
      });
    }
  }

  return result.sort((a, b) => b.precio - a.precio);
}

export function getPreciosLonja(semana: SemanaData, lonjaId: string): { cerealId: string; cerealNombre: string; precio: number; anterior: number; variacion: number }[] {
  const productos = semana.precios[lonjaId];
  if (!productos) return [];

  const result: { cerealId: string; cerealNombre: string; precio: number; anterior: number; variacion: number }[] = [];

  for (const [cerealId, item] of Object.entries(productos)) {
    const cereal = getCereal(cerealId);
    result.push({
      cerealId,
      cerealNombre: cereal?.nombre ?? cerealId,
      precio: item.precio,
      anterior: item.anterior,
      variacion: item.variacion,
    });
  }

  return result;
}

export function formatPrecio(precio: number): string {
  return precio.toFixed(2).replace('.', ',');
}

export function formatVariacion(variacion: number): string {
  if (variacion > 0) return `+${variacion.toFixed(2).replace('.', ',')}`;
  if (variacion < 0) return variacion.toFixed(2).replace('.', ',');
  return '0,00';
}

export function formatFecha(fecha: string): string {
  const date = new Date(fecha);
  const opciones: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' };
  return date.toLocaleDateString('es-ES', opciones);
}

export function getMesActual(): string {
  const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  return meses[new Date().getMonth()];
}

export function getAnioActual(): number {
  return new Date().getFullYear();
}
